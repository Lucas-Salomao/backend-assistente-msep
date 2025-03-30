import logging
import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

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


@tool
def futuro_digital(session_id: str, message: str):
    """Search for information about SENAI courses and training
    
    Args:
        ssession_id(str):user session identifier
        message(str):user message payload
    """
    logging.info(session_id)
    logging.info(message)
    logging.info('Endpoint futurodigital acessado')
    token = os.getenv("BEARER_TOKEN_FUTURO_DIGITAL")
    url = os.getenv("FUTURO_DITITAL_CHATBOT")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": message,
            }
        ],
        "session_id": session_id,
        "state": "DF",
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao fazer a requisição futurodigital: {e}")
        return {"error": str(e)}
    
tool = futuro_digital