from langchain_core.tools import tool
import logging
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    Tool,
    grounding,
)

load_dotenv()

# Verifica as credenciais
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise EnvironmentError("Credenciais do Google Cloud não encontradas!")

system_instruction_generico = """Você é uma ferramenta genérica para buscar informações na Internet, entretanto, quando o assunto for relacionado a busca de cursos, treinamentos, capacitações, vagas e oportunidades de estudo, buscará somente informações sobre o SENAI. Não buscará de nenhuma outra instituição. Se possível retorne links de referências para que o usuário possa navegar."""


chat_llm = ChatVertexAI(
    model_name=os.getenv("MODEL_ID"),
    temperature=0.1,
    max_output_tokens=8192,
)

llm_with_search = chat_llm.bind_tools([{"Google Search": {}}])

@tool
async def web_search(message: str) -> str:
    """Realiza uma busca na web por um termo

    Args:
        query (str): o termo a ser buscado

    Returns:
        str: os resultados da busca
    """
    logging.info('Endpoint generico acessado')
    try:
        # Gera a resposta usando o modelo
        response = await llm_with_search.ainvoke([
            SystemMessage(content=system_instruction_generico),
            HumanMessage(content=message)
        ])
        
        # Retorna o texto da resposta
        return response.content

    except Exception as e:
       logging.error(f"Erro ao fazer a requisição generico: {e}")
    return {"error": str(e)}

tool = web_search