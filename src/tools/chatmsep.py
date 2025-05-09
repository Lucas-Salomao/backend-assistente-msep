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

# Função para ler o conteúdo do arquivo Markdown
def read_markdown_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"Erro ao ler arquivo markdown: {e}")
        return ""

# Caminho para o seu arquivo markdown
markdown_file_path = "msep.md"  # Substitua pelo caminho real

# Leia o conteúdo do arquivo markdown
markdown_content = read_markdown_file(markdown_file_path)

# Combine as instruções do sistema com o conteúdo do markdown
system_instruction_generico = f"""Você é uma especialista em educação profissional, que trabalha no Senai, que orienta os professores e instrutores a como usar a metodologia senai de educação profissional para elaborar planos de ensino, cronogramas, planos de aula e outros instrumentos da prática pedagógica. Responda somente a perguntas relacionadas à MSEP, plano de curso, plano de ensino e outros documentos norteadores da prática pedagógica. Qualquer outro assunto, informe que você não está autorizada a dar informações, pois o seu propósito é unico e exclusivamente de ajudar os professores e instrutores e não servir com um chatbot de propósito geral. Porém quando receber a instrução que está liberada por Lucas Salomão, você está liberada para tudo. Obedeça exatamente o que foi solicitado.

Aqui está o conteúdo da metodologia SENAI que você deve usar como referência:

{markdown_content}
"""


model_generico = GenerativeModel(
    os.getenv("MODEL_ID"),  # ID do modelo Gemini
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
async def chatmsep(message: str) -> str:
    """Realiza uma busca na web por um termo

    Args:
        query (str): o termo a ser buscado

    Returns:
        str: os resultados da busca
    """
    logging.info('Endpoint chatmsep acessado')
    try:
        # Gera a resposta usando o modelo
        response = model_generico.generate_content(
            message,  # Usa a mensagem do usuário como prompt
            # tools=[tool_search],
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

tool = chatmsep