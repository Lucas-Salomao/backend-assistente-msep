import logging
import os
import google.generativeai as genai # Ou sua forma preferida de acessar o LLM
from google.generativeai.types import HarmCategory, HarmBlockThreshold # Para safety settings

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
    generation_config_dict = {
        "temperature": 0.1, "top_p": 0.95, "max_output_tokens": 8192, # Max tokens para PRO
        "response_mime_type": "text/plain",
    }
    # Configurações de segurança - ajuste conforme necessário
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    llm = genai.GenerativeModel(
        model_name=os.getenv('MODEL_ID'),
        generation_config=generation_config_dict,
        system_instruction="Você é um conversor de markdown para JSON de alta performance. Interprete o arquivo e gere apenas o JSON de saída. Não inclua a notação ````json```. Quero um formato puramente string.",
        safety_settings=safety_settings
    )
    prompt_convert = f"Converta para uma string JSON o markdown abaixo: {markdown_str}"
    json_str=await llm.generate_content_async(prompt_convert)
    
    return json_str.text