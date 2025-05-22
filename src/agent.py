import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.prebuilt import ToolExecutor
from src.tools import tools
from langchain_google_vertexai import ChatVertexAI
from google.cloud import aiplatform
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
import vertexai

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/msep.log", encoding= 'utf-8'),  # Salva logs em logs/app.log
        logging.StreamHandler()               # Exibe logs no console
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

STRING_POSTGRES="postgresql://"+os.getenv("PG_USER")+":"+os.getenv("PG_PASSWORD")+"@"+os.getenv("PG_HOST")+":"+os.getenv("PG_PORT")+"/"+os.getenv("PG_DATABASE")

# Verifica as credenciais
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise EnvironmentError("Credenciais do Google Cloud não encontradas!")

vertexai.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION", "us-central1"))

# Função para recuperar configurações do usuário
async def get_user_config(user_id: str):
    try:
        async with await AsyncConnection.connect(STRING_POSTGRES, autocommit=True) as conn:
            async with conn.cursor() as cur:
                query = """
                SELECT temperature, top_p 
                FROM user_configs 
                WHERE user_id = %s
                """
                await cur.execute(query, (user_id,))
                result = await cur.fetchone()
                if result:
                    return {"temperature": result[0], "top_p": result[1]}
                # Retorna valores padrão se não houver configuração
                return {"temperature": 0.7, "top_p": 1.0}
    except Exception as e:
        logger.error(f"Erro ao recuperar configuração do usuário {user_id}: {str(e)}")
        return {"temperature": 0.7, "top_p": 1.0}

# Configuração inicial do Gemini via Vertex AI (não mais global)
# llm será criado por requisição

async def get_llm(user_id: str):
    config = await get_user_config(user_id)
    return ChatVertexAI(
        model_name="gemini-2.0-flash-001",
        project=os.getenv("PROJECT_ID"),
        location=os.getenv("LOCATION", "us-central1"),
        temperature=config["temperature"],
        top_p=config["top_p"],
        max_output_tokens=8192
    )

# Configuração do checkpointer com asyncpg
async def get_checkpoint_connection():
    try:
        conn = await AsyncConnection.connect(STRING_POSTGRES, autocommit=True)
        logger.info("Conexão ao banco de dados estabelecida com sucesso")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

async def setup_checkpointer():
    """Cria as tabelas necessárias para o AsyncPostgresSaver, se não existirem."""
    try:
        conn = await get_checkpoint_connection()
        checkpointer = AsyncPostgresSaver(conn=conn)
        await checkpointer.setup()  # Cria as tabelas
        logger.info("Tabelas do checkpointer criadas ou verificadas com sucesso")
        await conn.close()
    except Exception as e:
        logger.error(f"Erro ao configurar o checkpointer: {e}")
        raise
    
async def create_user_configs_table(conn):
    """Cria a tabela user_configs se ela não existir."""
    try:
        async with conn.cursor() as cur:
            query = """
            CREATE TABLE IF NOT EXISTS user_configs (
                user_id VARCHAR(255) PRIMARY KEY,
                temperature FLOAT NOT NULL DEFAULT 0.7,
                top_p FLOAT NOT NULL DEFAULT 1.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            await cur.execute(query)
            logger.info("Tabela user_configs verificada/criada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar/verificar tabela user_configs: {e}")
        raise
    
async def setup_tables():
    """Cria a tabela necessária para o user_configs, se não existir."""
    try:
        conn = await get_checkpoint_connection()
        await create_user_configs_table(conn)  # Cria a tabela user_configs
        logger.info("Tabela do user_configs criada ou verificada com sucesso")
        await conn.close()
    except Exception as e:
        logger.error(f"Erro ao configurar o user_configs: {e}")
        raise

tool_prompt = PromptTemplate.from_template("""
retorne sempre "chatmsep" como ferramenta padrão, a menos que o usuário solicite especificamente outra ferramenta.
Retorne apenas o nome da ferramenta e mais nada.
""")

response_prompt = PromptTemplate.from_template("""
{tool_result}
Retorne o resultado sem modificações.
""")

title_prompt = PromptTemplate.from_template("""
Com base no input do usuário e na resposta do sistema, gere um título curto e descritivo para esta conversa.
O título deve ser conciso (no máximo 7 palavras) e capturar a essência do assunto discutido.

Input do usuário: {input}
Resposta do sistema: {response}

Título do da conversa
""")

class AgentState(TypedDict):
    input: str
    user_id: str
    thread_id: str
    tool_call: str
    tool_result: str
    response: str
    title: str  # Campo para armazenar o título da conversa
    messages: Annotated[list[str], "Mensagens acumuladas da conversa"]
    
    # Campos para processamento de PDF e Geração de Plano
    # Para extração inicial (a ferramenta recebe o markdown diretamente)
    pdf_markdown_content: Optional[str]

    # Para geração do plano (a ferramenta recebe o ID e busca o markdown)
    stored_markdown_id: Optional[str]
    plan_docente: Optional[str]
    plan_unidade_operacional: Optional[str]
    plan_nome_curso: Optional[str] # Pode vir do input do usuário ou da extração anterior
    plan_nome_uc: Optional[str]     # Pode vir do input do usuário ou da extração anterior
    plan_capacidades_tecnicas: Optional[List[str]]
    plan_capacidades_socioemocionais: Optional[List[str]]
    plan_estrategia: Optional[str]
    plan_tematica: Optional[str]
    # Outros dados extraídos que podem ser úteis para a ferramenta de geração do plano
    plan_extracted_data: Optional[Dict[str, Any]]
    
tool_map = {tool.name if hasattr(tool, 'name') else tool.__name__: tool for tool in tools}
tool_executor = ToolExecutor(tools)

# Mapeamento de argumentos para cada ferramenta
TOOL_ARGUMENTS = {
    "chatmsep": {"message": "input"},
    # "web_search": {"message": "input"}, # Se estiver usando
    "extract_full_plan_details": {
        "markdown_content": "pdf_markdown_content" # Vem do AgentState
    },
    "generate_teaching_plan": {
        "stored_markdown_id": "stored_markdown_id",
        "docente": "plan_docente",
        "unidade_operacional": "plan_unidade_operacional",
        "nome_curso": "plan_nome_curso",
        "nome_uc": "plan_nome_uc",
        "capacidades_tecnicas": "plan_capacidades_tecnicas",
        "capacidades_socioemocionais": "plan_capacidades_socioemocionais",
        "estrategia": "plan_estrategia",
        "tematica": "plan_tematica"
        # "extracted_initial_data": "plan_extracted_data" # Se passar como um dict
    }
}

async def identify_tool(state: AgentState) -> AgentState:
    user_input = state["input"]
    logger.info(f"Identificando ferramenta para input (comando): {user_input[:100]}...")
    
    current_messages = state.get("messages", []) # Preserva histórico de chat
    update_payload = {
        "tool_call": None, 
        "tool_result": None,
        "messages": current_messages
    } # Não resete outros campos do estado aqui

    if user_input.startswith("CMD_EXTRACT_FULL_PLAN_DETAILS:"): # NOVO COMANDO
        update_payload["tool_call"] = "extract_full_plan_details" # Nome da nova ferramenta
        # pdf_markdown_content é preenchido pelo endpoint no initial_payload
        logger.info(f"Comando direto para ferramenta de extração completa: {update_payload['tool_call']}")

    elif user_input.startswith("CMD_GENERATE_TEACHING_PLAN:"):
        update_payload["tool_call"] = "generate_teaching_plan" # Nome da nova ferramenta
        # Os campos stored_markdown_id, plan_docente, etc.
        # são preenchidos no AgentState pelo endpoint da API ANTES de chamar run_agent.
        logger.info(f"Comando direto para ferramenta de Geração de Plano: {update_payload['tool_call']}")
    else: # Lógica de chat normal (como antes)
        logger.info("Nenhum comando PDF/Plano direto, usando LLM para chat/busca.")
        prompt = tool_prompt.format(input=user_input)
        try:
            llm_for_tool_choice = await get_llm(state["user_id"])
            tool_choice_response = await llm_for_tool_choice.ainvoke(prompt)
            identified_tool = tool_choice_response.content.strip()
            
            if identified_tool and identified_tool.lower() != "none" and identified_tool in tool_map:
                update_payload["tool_call"] = identified_tool
            else:
                update_payload["tool_call"] = "chatmsep" 
            logger.info(f"LLM escolheu/default para chat: {update_payload['tool_call']}")
        except Exception as e:
            logger.error(f"Erro ao invocar LLM para identificação de ferramenta de chat: {e}", exc_info=True)
            update_payload["tool_result"] = json.dumps({"error": f"Erro ao identificar ferramenta de chat: {str(e)}"})
            # tool_call continua None, ou poderia default para chatmsep mesmo em erro

    state.update(update_payload)
    return state

async def execute_tool(state: AgentState) -> AgentState:
    if state["tool_call"]:
        logger.info(f"Executando ferramenta: {state['tool_call']}")
        if state["tool_call"] not in tool_map:
            state["tool_result"] = f"Ferramenta '{state['tool_call']}' não encontrada"
            logger.error(state["tool_result"])
            return state
        
        tool = tool_map[state["tool_call"]]
        
        # Preparar os argumentos dinamicamente com base no mapeamento
        tool_args_mapping = TOOL_ARGUMENTS.get(state["tool_call"], {})
        tool_input = {}
        for arg_name, state_key in tool_args_mapping.items():
            tool_input[arg_name] = state.get(state_key)
        logger.debug(f"Chamando ferramenta {state['tool_call']} com input: {tool_input}")   
        try:
            logger.info(tool_input)
            state["tool_result"] = await tool.ainvoke(tool_input)
            logger.info(f"Resultado da ferramenta {state['tool_call']}: {state['tool_result']}")
        except Exception as e:
            logger.error(f"Erro ao executar ferramenta {state['tool_call']}: {str(e)}", exc_info=True)
            state["tool_result"] = f"Erro ao executar {state['tool_call']}: {str(e)}"      
    else:
        logger.info("Nenhuma ferramenta a ser executada")
    return state

async def generate_response(state: AgentState) -> AgentState:
    logger.info("Gerando resposta final")
    llm = await get_llm(state["user_id"])
    tool_result = state["tool_result"]
    prompt = response_prompt.format(
        messages="\n".join(state["messages"]),
        input=state["input"],
        # tool_endereco=tool_endereco,
        # tool_mapa=tool_mapa,
        tool_result=state["tool_result"] if state["tool_result"] else "Nenhum resultado de ferramenta",
    )
    state["response"] = (await llm.ainvoke(prompt)).content
    state["messages"] = state.get("messages", []) + [f"User: {state['input']}", f"Agent: {state['response']}"]
    logger.info(f"Resposta gerada: {state['response']}")
    return state

async def generate_title(state: AgentState) -> AgentState:
    """Gera um título para a conversa baseado no input do usuário e na resposta."""
    # Se já tiver um título, mantém o mesmo
    if state.get("title"):
        logger.info(f"Mantendo título existente: {state['title']}")
        return state
        
    # Gera um novo título se tivermos input e resposta
    if state["input"] and state["response"]:
        logger.info("Gerando título para a conversa")
        prompt = title_prompt.format(
            input=state["input"],
            response=state["response"]
        )
        
        try:
            llm = await get_llm(state["user_id"])
            state["title"] = (await llm.ainvoke(prompt)).content.strip()
            logger.info(f"Título gerado: {state['title']}")
        except Exception as e:
            logger.error(f"Erro ao gerar título: {str(e)}")
            state["title"] = "Nova Conversa"  # Título padrão em caso de falha
    else:
        logger.info("Definindo título padrão 'Nova Conversa'")
        state["title"] = "Nova Conversa"  # Título padrão
        
    return state

# Construção do grafo
workflow = StateGraph(AgentState)
workflow.add_node("identify_tool", identify_tool)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("generate_response", generate_response)
workflow.add_node("generate_title", generate_title)  # Adiciona o novo nó
workflow.set_entry_point("identify_tool")
workflow.add_edge("identify_tool", "execute_tool")
workflow.add_edge("execute_tool", "generate_response")
workflow.add_edge("generate_response", "generate_title")  # Modifica o fluxo
workflow.add_edge("generate_title", END) # Finaliza após gerar o título

# Compila o grafo com checkpointer
# agent = workflow.compile(checkpointer=checkpointer)
agent=None

async def initialize_agent():
    global agent
    if agent is None:
        conn = await get_checkpoint_connection()
        checkpointer = AsyncPostgresSaver(conn=conn)
        await checkpointer.setup()  # Garante que as tabelas sejam criadas
        agent = workflow.compile(checkpointer=checkpointer)
    return agent

# Função assíncrona para rodar o agente
async def run_agent(input: str, user_id: str, thread_id: str) -> dict:
    logger.info(f"Iniciando agente para user_id={user_id}, thread_id={thread_id}, input={input}")
    await initialize_agent()  # Inicializa o agente na primeira chamada
    config = {"configurable": {"thread_id": thread_id},
              "metadata": {"user_id": user_id}}
    
    # Recupera o estado anterior do checkpoint, se existir
    previous_state = await agent.aget_state(config)
    
    # Obtém as mensagens anteriores se existirem
    initial_messages = []
    if previous_state and "messages" in previous_state.values:
        initial_messages = previous_state.values["messages"]
    
    # Obtém o título anterior se existir
    title = None
    if previous_state and "title" in previous_state.values:
        title = previous_state.values["title"]
        logger.info(f"Título recuperado do estado anterior: {title}")
    
    initial_state = {
        "input": input,
        "user_id": user_id,
        "thread_id": thread_id,
        "tool_call": None,
        "tool_result": None,
        "response": None,
        "title": title,  # Pode ser None para novas conversas
        "messages": initial_messages
    }
    result = await agent.ainvoke(initial_state, config=config)  # Chamada assíncrona do grafo
    logger.info(f"Agente concluído com resposta: {result['response']}")
    logger.info(f"Título da conversa: {result['title']}")
    return {
        "response": result["response"],
        "title": result["title"]
    }