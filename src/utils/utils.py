import logging
import os
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

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

json_converter_llm = ChatVertexAI(
    model_name=os.getenv("MODEL_ID"),
    temperature=0.1, # Temperatura baixa para respostas previsíveis
    top_p=0.95,
    max_output_tokens=8192
)

async def cleanup_temp_file(file_path: str):
    """Remove o arquivo temporário após o envio."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo temporário deletado: {file_path}")
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo temporário {file_path}: {str(e)}")
        
async def convert_markdown_to_json(markdown_str: str):
    """Converte o plano de ensino em Markdown para um dicionário JSON."""
    instrucao_sistema = "Você é um conversor de markdown para JSON de alta performance. Interprete o arquivo e gere apenas o JSON de saída. Não inclua a notação ```json```. Quero um formato puramente texto."
    
    prompt_usuario = f"Converta para uma string JSON o markdown abaixo: {markdown_str}"

    try:
        response = await json_converter_llm.ainvoke([
            SystemMessage(content=instrucao_sistema),
            HumanMessage(content=prompt_usuario)
        ])
        return response.content
    except Exception as e:
        logger.error(f"Erro ao converter markdown para JSON: {e}")
        # Retorna um JSON de erro em caso de falha
        return '{"error": "Falha ao converter o conteúdo para JSON."}'