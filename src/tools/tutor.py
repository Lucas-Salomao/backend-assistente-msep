from langchain_core.tools import tool
import logging
import google.generativeai as genai
import os
from dotenv import load_dotenv

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

# Configuração da API do Gemini 
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Configuração do modelo
generation_config = {
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

modelLM = genai.GenerativeModel(
    model_name="learnlm-1.5-pro-experimental",
    generation_config=generation_config,
    system_instruction="Você é capaz de montar planos de estudo para alunos e planos de aula para docentes. Você também é capaz de entender o modo de aprendizagem de cada usuário e, de forma adaptativa, fazer o usuário chegar ao seu objetivo na aprendizagem. Interaja com o usuário para que o objetivo na aprendizagem seja alcançado.",
)

@tool
def tutor(message: str, history: list = None):
    """Creates study plans and guides the user on ways to study to achieve a specific goal. Provides guided tutoring to the user during the learning process.
    
    Args:
        message (str): User message payload
        history (list, optional): List of previous messages in the conversation, in the format [{"role": "user", "parts": ["message"]}, {"role": "model", "parts": ["response"]}]
    """
    logging.info('Endpoint tutor acessado')
    try:
        # Converte o histórico para o formato esperado pelo Gemini
        chat_history = history if history else []
        # Garantir que o histórico esteja no formato correto
        formatted_history = []
        for msg in chat_history:
            if "User: " in msg:
                formatted_history.append({"role": "user", "parts": [msg.replace("User: ", "")]})
            elif "Agent: " in msg:
                formatted_history.append({"role": "model", "parts": [msg.replace("Agent: ", "")]})

        chat_session = modelLM.start_chat(history=formatted_history)
        response = chat_session.send_message(message)
        return response.text  # Retorna apenas o texto da resposta
    except Exception as e:
        logging.error(f"Erro na requisição tutor: {e}")
        return {"error": str(e)}

tool = tutor