import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langgraph.prebuilt import ToolExecutor
from tools import tools
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
        logging.FileHandler("logs/nai.log", encoding= 'utf-8'),  # Salva logs em logs/app.log
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

# Configuração do Gemini via Vertex AI (assíncrono)
llm = ChatVertexAI(
    model_name="gemini-2.0-flash-001",
    project=os.getenv("PROJECT_ID"),
    location=os.getenv("LOCATION", "us-central1"),
    temperature=0.7,
    max_output_tokens=8192
)
logger.info(f"LLM inicializado: {llm is not None}")

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

tool_prompt = PromptTemplate.from_template("""
retorne sempre "chatmsep" como ferramenta padrão, a menos que o usuário solicite especificamente outra ferramenta.
Retorne apenas o nome da ferramenta e mais nada.
""")

response_prompt = PromptTemplate.from_template("""
{tool_result}
Retorne o resultado sem modificações.
""")

class AgentState(TypedDict):
    input: str
    user_id: str
    thread_id: str
    tool_call: str
    tool_result: str
    response: str
    messages: Annotated[list[str], "Mensagens acumuladas da conversa"]
    
tool_map = {tool.name if hasattr(tool, 'name') else tool.__name__: tool for tool in tools}
tool_executor = ToolExecutor(tools)

# Mapeamento de argumentos para cada ferramenta
TOOL_ARGUMENTS = {
    "web_search": {"message": "input"},
    "chatmsep": {"message": "input"}
}

async def identify_tool(state: AgentState) -> AgentState:
    logger.info(f"Identificando ferramenta para input: {state['input']}")
    prompt = tool_prompt.format(input=state["input"])
    tool_call = (await llm.ainvoke(prompt)).content.strip()  # Chamada assíncrona ao LLM
    state["tool_call"] = tool_call if tool_call != "none" else None
    logger.info(f"Ferramenta identificada: {state['tool_call']}")
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

# Construção do grafo
workflow = StateGraph(AgentState)
workflow.add_node("identify_tool", identify_tool)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("generate_response", generate_response)
workflow.set_entry_point("identify_tool")
workflow.add_edge("identify_tool", "execute_tool")
workflow.add_edge("execute_tool", "generate_response")
workflow.add_edge("generate_response", END)

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
async def run_agent(input: str, user_id: str, thread_id: str) -> str:
    logger.info(f"Iniciando agente para user_id={user_id}, thread_id={thread_id}, input={input}")
    await initialize_agent()  # Inicializa o agente na primeira chamada
    config = {"configurable": {"thread_id": thread_id}}
    
    # Recupera o estado anterior do checkpoint, se existir
    previous_state = await agent.aget_state(config)
    initial_messages = previous_state.values.get("messages", []) if previous_state else []
    
    initial_state = {
        "input": input,
        "user_id": user_id,
        "thread_id": thread_id,
        "tool_call": None,
        "tool_result": None,
        "response": None,
        "messages": []
    }
    result = await agent.ainvoke(initial_state, config=config)  # Chamada assíncrona do grafo
    logger.info(f"Agente concluído com resposta: {result['response']}")
    return result["response"]