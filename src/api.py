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
from models.models import RequestBody, PlanGenerationBody, PlanGenerationResponse, GetThreadsRequest, GetThreadsResponse, ChatHistoryRequest, MessageInfo, ChatHistoryResponse
from psycopg import AsyncConnection  # Adiciona esta importação
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent import get_checkpoint_connection

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
        result = await run_agent(  # Await na chamada assíncrona
            input=body.message,
            user_id=body.userId,
            thread_id=body.threadId,
        )
        return {
            "message": result["response"], 
            "title": result["title"],  # Adiciona o título
            "user_id": body.userId, 
            "thread_id": body.threadId
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/health/", response_model=dict)
async def health_check():
    try:
        logger.info("Health check solicitado")
        return {"status": "servidor rodando"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/get_threads/", response_model=GetThreadsResponse)
async def get_threads(body: GetThreadsRequest):
    try:
        logger.info(f"Endpoint get_threads solicitado para user_id: {body.userId}")
        async with await AsyncConnection.connect(
            f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}",
            autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                query = """
                SELECT DISTINCT thread_id 
                FROM checkpoints 
                WHERE (metadata->>'user_id') = %s
                """
                await cur.execute(query, (body.userId,))
                thread_ids = [row[0] async for row in cur]
        
        return GetThreadsResponse(
            userId=body.userId,
            all_threads=thread_ids
        )
    except Exception as e:
        logger.error(f"Erro ao recuperar threads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_history/", response_model=ChatHistoryResponse)
async def get_chat_history(body: ChatHistoryRequest):
    try:
        logger.info(f"Endpoint chat_history solicitado para thread_id: {body.threadId}")
        conn = await get_checkpoint_connection()
        checkpointer = AsyncPostgresSaver(conn=conn)
        
        config = {"configurable": {"thread_id": body.threadId}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if not checkpoint_tuple or 'messages' not in checkpoint_tuple.checkpoint['channel_values']:
            return ChatHistoryResponse(threadId=body.threadId, messages=[],title=None)
        
        messages = checkpoint_tuple.checkpoint['channel_values']['messages']
        title = checkpoint_tuple.checkpoint['channel_values'].get('title')
        
        extracted_messages = [
            MessageInfo(
                type=type(msg).__name__,
                content=msg if isinstance(msg, str) else msg.content,
                additional_info={
                    "id": getattr(msg, 'id', None),
                    **({"tool_calls": msg.tool_calls} if hasattr(msg, 'tool_calls') else {}),
                    **({"tool_call_id": msg.tool_call_id} if hasattr(msg, 'tool_call_id') else {})
                }
            ) for msg in messages
        ]
        
        await conn.close()
        return ChatHistoryResponse(
            threadId=body.threadId,
            messages=extracted_messages,
            title=title
        )
    except Exception as e:
        logger.error(f"Erro ao recuperar histórico de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT')), timeout_keep_alive=300)