import logging
import platform
import asyncio
from asyncio import WindowsSelectorEventLoopPolicy
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import run_agent
import os
from dotenv import load_dotenv
from tts import text_to_speach
from models.models import RequestBody, TTSRequestBody
from utils.utils import cleanup_temp_file

# Importa a middleware CORS <<<<<<----- ADICIONADO
from fastapi.middleware.cors import CORSMiddleware

# Configuração específica para Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Configuração do logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/nai.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

app = FastAPI(title="NAI API", description="API assíncrona da NAI com Gemini e PostgreSQL, usando Langgraph e Langchain", version="1.0")

# --- CONFIGURAÇÃO DO CORS --- <<<<<<----- ADICIONADO
# Lista de origens permitidas. "*" permite qualquer origem.
# Para produção, é MAIS SEGURO listar explicitamente as origens do seu frontend:
# origins = [
#     "http://localhost:5000",
#     "https://seu-frontend-em-producao.com",
# ]
origins = ["*"] # Permite qualquer origem (para o seu pedido atual)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Permite as origens definidas acima
    allow_credentials=True, # Permite cookies/credenciais (se necessário) -> CUIDADO: Se True, origins não pode ser ["*"]! Mude para False se usar ["*"] ou liste origens específicas. Vamos usar False com ["*"].
    allow_methods=["*"],    # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],    # Permite todos os cabeçalhos
)
# --- FIM DA CONFIGURAÇÃO DO CORS ---

@app.post("/chat/", response_model=dict)
async def process_message(body: RequestBody):
    try:
        logger.info("endpoint CHAT solicitado")
        response = await run_agent(  # Await na chamada assíncrona
            input=body.message,
            user_id=body.userId,
            thread_id=body.threadId,
            latitude="23.5505",
            longitude="46.6333",
        )
        return {"message": response, "user_id": body.userId, "thread_id": body.threadId}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/health/", response_model=dict)
async def health_check():
    try:
        logger.info("Health check solicitado")
        return {"status": "servidor rodando"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
@app.post("/tts/")
async def tts_endpoint(body: TTSRequestBody, background_tasks: BackgroundTasks):
    logger.info(f"Requisição TTS recebida: message={body.message}")
    try:
        if not body.message:
            raise HTTPException(status_code=400, detail="Nenhum texto fornecido para síntese")

        # Gera o áudio usando a função encapsulada
        audio_file_path = await text_to_speach(body.message)
        
        # Adiciona a tarefa de limpeza em background após o envio
        background_tasks.add_task(cleanup_temp_file, audio_file_path)

        # Retorna o arquivo como resposta
        return FileResponse(
            path=audio_file_path,
            media_type='audio/mpeg',
            filename='speech.mp3',
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"Erro no endpoint TTS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar solicitação de texto para fala: {str(e)}")  

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT')), timeout_keep_alive=300)