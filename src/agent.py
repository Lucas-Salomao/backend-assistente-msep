import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional, List, Dict, Any, cast
from langgraph.prebuilt import ToolExecutor
from src.tools import tools
import vertexai
from langchain_google_vertexai import ChatVertexAI
from google.cloud import aiplatform
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
import json
from src.models.models import SituacaoAprendizagemInput

# --- Lógica para criar a pasta de logs ---
# 2. Defina o nome do diretório e o caminho completo do arquivo de log
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "msep.log")

# 3. Crie o diretório de logs se ele não existir
os.makedirs(LOG_DIR, exist_ok=True)
# O argumento exist_ok=True garante que nenhum erro será lançado se a pasta já existir.

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding= 'utf-8'),  # Salva logs em logs/app.log
        logging.StreamHandler()               # Exibe logs no console
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

if os.getenv("PROJECT_ID"):
    vertexai.init(project=os.getenv("PROJECT_ID"), location=os.getenv("LOCATION", "us-central1"))
else:
    logger.warning("PROJECT_ID não definido no ambiente.")
    
# Verifica as credenciais
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise EnvironmentError("Credenciais do Google Cloud não encontradas!")

STRING_POSTGRES="postgresql://"+os.getenv("PG_USER")+":"+os.getenv("PG_PASSWORD")+"@"+os.getenv("PG_HOST")+":"+os.getenv("PG_PORT")+"/"+os.getenv("PG_DATABASE")

# Verifica as credenciais
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise EnvironmentError("Credenciais do Google Cloud não encontradas!")


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
        model_name=os.getenv("MODEL_ID"), # O parâmetro é 'model_name'
        project=os.getenv("PROJECT_ID"),
        location=os.getenv("LOCATION", "us-central1"),
        temperature=config["temperature"],
        top_p=config["top_p"],
        max_output_tokens=8192
        # Note que não há 'convert_system_message_to_human' aqui
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
    
async def create_user_plans_table(conn):
    """Cria a tabela user_plans se ela não existir."""
    try:
        async with conn.cursor() as cur:
            query = """
            CREATE TABLE IF NOT EXISTS user_plans (
                    id UUID PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    thread_id VARCHAR(255) NOT NULL,
                    course_plan_id VARCHAR(255) NOT NULL,
                    gcs_blob_name VARCHAR(1024) NOT NULL, -- Caminho para o arquivo no GCS
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """
            await cur.execute(query)
            logger.info("Tabela user_plans verificada/criada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar/verificar tabela user_plans: {e}")
        raise
    
async def setup_tables():
    """Cria a tabela necessária para o user_configs, se não existir."""
    try:
        conn = await get_checkpoint_connection()
        await create_user_configs_table(conn)  # Cria a tabela user_configs
        await create_user_plans_table(conn) # Cria a tabela user_plans
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
Retorne o resultado sem modificações. Não adicione notação de bloco de código ou json. Não adicione ```json```.
""")

title_prompt = PromptTemplate.from_template("""
Com base no input do usuário e na resposta do sistema, gere um único título curto e descritivo para esta conversa.
O título deve ser conciso (no máximo 7 palavras), objetivo e capturar a essência do assunto discutido. Não gere sugestões de títulos, gere apenas o título conforme diretrizes.

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
    plan_turma: Optional[str]
    plan_nome_uc: Optional[str]     # Pode vir do input do usuário ou da extração anterior
    
    # A lista de SAs, onde cada SA tem seus próprios detalhes
    plan_situacoes_aprendizagem: Optional[List[Dict[str, Any]]] # Lista de SAs como dicts
                                                                # Cada dict terá: capacidades_tecnicas, socioemocionais, estrategia, tema_desafio
                                                                
    plan_horarios: Optional[List[Dict[str, str]]] # Horários gerais para a UC
    
    plan_extracted_data: Optional[Dict[str, Any]] # Usado pela ferramenta de extração, não diretamente pela de geração
    
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
        "turma": "plan_turma",
        "nome_uc": "plan_nome_uc",
        "situacoes_aprendizagem_param": "plan_situacoes_aprendizagem",
        "horarios_param": "plan_horarios"
    }
}

async def identify_tool(state: AgentState) -> AgentState:
    user_input = state["input"]
    logger.info(f"Identificando ferramenta para input (comando): {user_input}...")
    
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
        logger.info("Nenhum comando direto, usando LLM para chat.")
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

    # Usar type assertion para state
    cast_state = cast(Dict[str, Any], state)
    cast_state.update(update_payload)
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
        tool_input : Dict[str, Any] = {} # Definir o tipo explicitamente
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
    logger.info(f"Gerando resposta final para tool_call: {state.get('tool_call')}")
    
    current_tool_call = state.get("tool_call")
    tool_result_from_state = state.get("tool_result", "") # Garante que não seja None

    final_agent_response: str = ""

    # Se a ferramenta é uma das que já retorna o JSON formatado que queremos como "resposta da operação"
    if current_tool_call in ["generate_teaching_plan","extract_full_plan_details"]:
        if tool_result_from_state:
            try:
                # Apenas valida se é JSON, mas a resposta do agente será a string JSON
                json.loads(tool_result_from_state) 
                final_agent_response = tool_result_from_state
                logger.info(f"Usando tool_result diretamente como resposta para a ferramenta '{current_tool_call}'.")
            except json.JSONDecodeError as e:
                logger.error(f"Tool_result da ferramenta '{current_tool_call}' não é JSON válido: {e}. Conteúdo: {tool_result_from_state}...")
                final_agent_response = json.dumps({"error": f"Resultado inválido da ferramenta {current_tool_call}.", "details": str(e)})
        else:
            logger.warning(f"Nenhum tool_result para a ferramenta '{current_tool_call}'.")
            final_agent_response = json.dumps({"error": f"Nenhum resultado produzido pela ferramenta {current_tool_call}."})
    
    # Se não foi tratado acima (ex: é chatmsep ou outra ferramenta textual, ou erro no JSON)
    if not final_agent_response:
        logger.info(f"Ferramenta '{current_tool_call}' não tratada diretamente ou tool_result ausente/inválido. Usando LLM para resposta final.")
        llm = await get_llm(state["user_id"])
        prompt_str_for_llm = response_prompt.format(
            messages="\n".join(state.get("messages", [])), # Histórico
            input=state.get("input", ""), # Input original que disparou a tool/chat
            tool_result=tool_result_from_state if tool_result_from_state else "Nenhuma ação de ferramenta específica foi realizada ou não produziu resultado para exibir."
        )
        try:
            final_agent_response = (await llm.ainvoke(prompt_str_for_llm)).content
            logger.info("Resposta final gerada pelo LLM do nó generate_response.")
        except Exception as e_llm_resp:
            logger.error(f"Erro ao gerar resposta com LLM no nó generate_response: {e_llm_resp}", exc_info=True)
            final_agent_response = json.dumps({"error": "Falha crítica ao processar a resposta final."}) # Retorna JSON de erro

    state["response"] = final_agent_response
    # Adiciona o input original e a resposta final ao histórico.
    # Se a resposta for um JSON gigante (como o plano), ele vai para o histórico.
    state["messages"] = state.get("messages", []) + [f"User: {state.get('input', '')}", f"Agent: {state['response']}"]
    logger.info(f"Nó generate_response concluído. Resposta (início): {state['response'][:200]}...")
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
async def run_agent(
    input_command_or_message: str,
    user_id: str,
    thread_id: str,
    initial_payload: Optional[Dict[str, Any]] = None
) -> Dict:
    logger.info(f"Iniciando agente para user_id={user_id}, thread_id={thread_id}, input='{input_command_or_message}...'")
    await initialize_agent()
    config = {"configurable": {"thread_id": thread_id}, "metadata": {"user_id": user_id}}
    
    current_state_dict = {}
    if not initial_payload:
        previous_state_tuple = await agent.aget_state(config)
        if previous_state_tuple:
            current_state_dict = previous_state_tuple.values
            logger.info(f"Estado anterior recuperado para thread_id={thread_id}")
        else:
            logger.info(f"Nenhum estado anterior encontrado para thread_id={thread_id}, iniciando novo.")

    initial_messages = current_state_dict.get("messages", [])
    current_title = current_state_dict.get("title")
    
    # Cria um dicionário com todos os campos esperados por AgentState e seus tipos default/None
    current_state_dict.update({
        "input": input_command_or_message,
        "user_id": user_id,
        "tool_call": None,
        "tool_result": None,
        "response": None,
    })
    
    if "messages" not in current_state_dict:
        current_state_dict["messages"] = []

    if initial_payload:
        logger.info(f"Aplicando initial_payload ao estado: {list(initial_payload.keys())}")
        current_state_dict.update(initial_payload)
        if "input" in initial_payload: # Se o payload definir um input, ele tem precedência
            current_state_dict["input"] = initial_payload["input"]
        # Para operações como Geração de Plano ou Extração, o histórico de chat não deve ser carregado do checkpoint,
        # pois são operações discretas.
        if "CMD_GENERATE_TEACHING_PLAN" in input_command_or_message or \
           "CMD_EXTRACT_FULL_PLAN_DETAILS" in input_command_or_message:
            if "messages" not in initial_payload: # A menos que o payload force mensagens
                 current_state_dict["messages"] = []
            if "title" not in initial_payload: # E não deve carregar título anterior
                current_state_dict["title"] = None

    # Garantir que todos os Optional[List] sejam listas e não None antes de passar para AgentState
    for key in ["plan_situacoes_aprendizagem", "plan_horarios"]:
        if current_state_dict.get(key) is None:
            current_state_dict[key] = []
    
    # O `initial_payload` fornecido por `api.py` para generate_teaching_plan
    # já conterá "plan_situacoes_aprendizagem" devidamente preenchido.
    if "plan_situacoes_aprendizagem" in initial_payload if initial_payload else False:
        # Certificando que o que está em current_state_dict é o que veio do initial_payload
        # e que é uma lista de dicts, como esperado pela ferramenta.
        # O Pydantic já validou o formato em api.py
        valid_sas = []
        if isinstance(initial_payload.get("plan_situacoes_aprendizagem"), list): # type: ignore
            for sa_input in initial_payload["plan_situacoes_aprendizagem"]: # type: ignore
                if isinstance(sa_input, dict): # Se já for dict, ótimo
                    valid_sas.append(sa_input)
                elif hasattr(sa_input, 'model_dump'): # Se for um objeto Pydantic
                    valid_sas.append(sa_input.model_dump())
                else:
                    logger.warning(f"Item SA não é dict nem Pydantic model no initial_payload: {type(sa_input)}")
            current_state_dict["plan_situacoes_aprendizagem"] = valid_sas
        else:
            logger.warning("plan_situacoes_aprendizagem no initial_payload não é uma lista.")
            current_state_dict["plan_situacoes_aprendizagem"] = []

    # Converte o dicionário para AgentState, o LangGraph lida com a tipagem.
    # O `cast` é usado para satisfazer o mypy, mas o LangGraph internamente
    # espera um dicionário que corresponda às chaves e tipos do TypedDict.
    final_initial_state_for_agent = cast(AgentState, current_state_dict)
    logger.debug(f"Estado inicial para a invocação do agente (thread {thread_id}): { {k: (str(v)[:100] + '...' if isinstance(v, str) and len(v) > 100 else v) for k, v in final_initial_state_for_agent.items()} }")
    result = await agent.ainvoke(final_initial_state_for_agent, config=config)
    
    logger.info(f"Agente (thread {thread_id}) concluído. Resposta: '{str(result.get('response'))}...', Título: {result.get('title')}")
    return {
        "response": result.get("response"),
        "title": result.get("title"),
        "thread_id": thread_id,
        "user_id": user_id
    }