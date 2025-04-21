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
from models.models import RequestBody

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
        logging.FileHandler("logs/msep.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis do .env
load_dotenv()

app = FastAPI(title="Assistente Virtual MSEP API", description="API assíncrona do Assistente Virtual da MSEP com Gemini e PostgreSQL, usando Langgraph e Langchain", version="1.0")

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
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT')), timeout_keep_alive=300)