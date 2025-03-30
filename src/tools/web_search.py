from langchain_core.tools import tool
import logging
import google.generativeai as genai
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


model_generico = GenerativeModel(
    "gemini-1.5-flash-002",
    system_instruction=system_instruction_generico,  # Instruções de sistema diretamente no modelo
)

# Use Google Search for grounding
tool_search = Tool.from_google_search_retrieval(
    grounding.GoogleSearchRetrieval(
        # Optional: For Dynamic Retrieval
        dynamic_retrieval_config=grounding.DynamicRetrievalConfig(
            dynamic_threshold=0.7,
        )
    )
)

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
        response = model_generico.generate_content(
            message,  # Usa a mensagem do usuário como prompt
            tools=[tool_search],
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )
        
        # Retorna o texto da resposta
        return response.text

    except Exception as e:
       logging.error(f"Erro ao fazer a requisição generico: {e}")
    return {"error": str(e)}

tool = web_search