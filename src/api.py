import logging
import platform
import asyncio
from typing import Optional, Optional, List, Dict, Any
from fastapi import FastAPI, File, HTTPException, Request, BackgroundTasks, Form, UploadFile
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
from psycopg import AsyncConnection  # Adiciona esta importação
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .agent import run_agent, get_checkpoint_connection, setup_tables, setup_checkpointer
from .document_store import setup_document_storage, store_markdown_document
from .pdf_processor import convert_pdf_to_markdown
import json # Para carregar strings JSON
import uuid # Para gerar IDs
from .models.models import (
    RequestBody,
    GetThreadsRequest, GetThreadsResponse,
    ChatHistoryRequest, MessageInfo, ChatHistoryResponse,
    ThreadInfo, GetThreadsWithTitlesRequest, GetThreadsWithTitlesResponse,
    ModelConfigRequest,
    FullPlanDetailsResponse, # Nosso modelo de resposta para extração
    PlanGenerationBodyWithStoredId, PlanGenerationResponse # Para geração do plano
)

# Importa a middleware CORS <<<<<<----- ADICIONADO
from fastapi.middleware.cors import CORSMiddleware

# Configuração específica para Windows
if platform.system() == 'Windows':
    from asyncio import WindowsSelectorEventLoopPolicy
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

@app.on_event("startup")
async def startup_event():
    logger.info("Inicializando o backend...")
    await setup_checkpointer()
    await setup_tables()
    await setup_document_storage()
    logger.info("Eventos de startup concluídos.")

@app.post("/chat", response_model=dict)
async def process_message(body: RequestBody):
    try:
        logger.info("endpoint CHAT solicitado")
        result = await run_agent(  # Await na chamada assíncrona
            input_command_or_message=body.message,
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
    
@app.get("/health", response_model=dict)
async def health_check():
    try:
        logger.info("Health check solicitado")
        return {"status": "servidor rodando"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/get_threads", response_model=GetThreadsResponse)
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

@app.post("/chat_history", response_model=ChatHistoryResponse)
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

@app.post("/get_threads_with_titles", response_model=GetThreadsWithTitlesResponse)
async def get_threads_with_titles(body: GetThreadsWithTitlesRequest):
    try:
        logger.info(f"Endpoint get_threads_with_titles solicitado para user_id: {body.userId}")
        async with await AsyncConnection.connect(
            f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}",
            autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                query = """
                SELECT thread_id, (metadata->'writes'->'generate_title'->>'title') AS title
                FROM (
                    SELECT thread_id, metadata,
                           ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY (metadata->>'step')::int DESC) AS rn
                    FROM checkpoints
                    WHERE (metadata->>'user_id') = %s
                ) t
                WHERE rn = 1;
                """
                await cur.execute(query, (body.userId,))
                threads = [
                    ThreadInfo(thread_id=row[0], title=row[1])
                    async for row in cur
                ]
        
        return GetThreadsWithTitlesResponse(
            userId=body.userId,
            threads=threads
        )
    except Exception as e:
        logger.error(f"Erro ao recuperar threads com títulos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_thread{thread_id}")
async def delete_thread(thread_id: str, user_id: str = Form(...)):
    try:
        logger.info(f"Endpoint delete_thread solicitado para thread_id: {thread_id} e user_id: {user_id}")
        async with await AsyncConnection.connect(
            f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}",
            autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                # Verifica se o thread_id pertence ao user_id
                query_check = """
                SELECT EXISTS (
                    SELECT 1 FROM checkpoints 
                    WHERE thread_id = %s AND (metadata->>'user_id') = %s
                )
                """
                await cur.execute(query_check, (thread_id, user_id))
                exists = await cur.fetchone()
                if not exists[0]:
                    raise HTTPException(status_code=404, detail="Thread not found for this user")

                # Exclui o thread
                query_delete = """
                DELETE FROM checkpoints 
                WHERE thread_id = %s AND (metadata->>'user_id') = %s
                """
                await cur.execute(query_delete, (thread_id, user_id))
                await conn.commit()

        return {"message": "Thread deleted successfully", "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Erro ao excluir thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/configure_model")
async def configure_model(config: ModelConfigRequest):
    try:
        logger.info(f"Endpoint configure_model solicitado para user_id: {config.user_id}, temperature={config.temperature}, top_p={config.top_p}")
        
        # Atualiza o banco de dados
        async with await AsyncConnection.connect(
            f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}",
            autocommit=True
        ) as conn:
            async with conn.cursor() as cur:
                query = """
                INSERT INTO user_configs (user_id, temperature, top_p)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET temperature = EXCLUDED.temperature,
                    top_p = EXCLUDED.top_p,
                    updated_at = CURRENT_TIMESTAMP
                """
                await cur.execute(query, (config.user_id, config.temperature, config.top_p))

        return {
            "message": "Model configuration updated successfully for user",
            "user_id": config.user_id,
            "temperature": config.temperature,
            "top_p": config.top_p
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro ao configurar modelo para user_id {config.user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/pdf/extract_full_details", response_model=FullPlanDetailsResponse)
async def pdf_extract_full_plan_details(
    file: UploadFile = File(..., description="Arquivo PDF do plano de curso completo."),
    user_id: str = Form(..., description="ID do usuário."),
    thread_id: str = Form(..., description="ID da conversa/sessão original para associar o documento."),
    original_pdf_filename: Optional[str] = Form(None, description="Nome original do arquivo PDF (opcional).")
):
    operation_description = "extract_full_plan_details"
    effective_filename = original_pdf_filename or file.filename or "unknown.pdf"
    logger.info(f"Endpoint /{operation_description} chamado por user: {user_id}, thread_orig: {thread_id}, file: {effective_filename}")
    
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido. Apenas PDF é aceito.")

    try:
        markdown_content = await convert_pdf_to_markdown(file)
        
        # Armazena o documento e associa ao user_id e thread_id originais
        stored_doc_id = await store_markdown_document(
            user_id=user_id,
            thread_id=thread_id, # Associa o documento armazenado ao thread_id da conversa principal
            markdown_content=markdown_content,
            original_pdf_filename=effective_filename
        )
        logger.info(f"Markdown para '{effective_filename}' ({operation_description}) armazenado com ID: {stored_doc_id}")

        # Cria um thread_id único para a operação do agente LangGraph (não polui o histórico da conversa principal)
        agent_operation_thread_id = f"op_{operation_description}_{uuid.uuid4().hex[:12]}"

        agent_initial_payload = {
            "user_id": user_id, # Para config do LLM do agente
            "thread_id": agent_operation_thread_id,
            "pdf_markdown_content": markdown_content, # Conteúdo para a ferramenta de extração
            "messages": [] # Operação discreta, sem histórico de chat prévio
        }
        
        agent_result_dict = await run_agent(
            input_command_or_message=f"CMD_EXTRACT_FULL_PLAN_DETAILS:{effective_filename}", # Comando gatilho
            user_id=user_id, # Passa user_id para run_agent
            thread_id=agent_operation_thread_id, # Thread específico da operação
            initial_payload=agent_initial_payload # Passa dados pré-processados
        )
        
        full_details_json_str = agent_result_dict.get("response")
        if not full_details_json_str:
            logger.error(f"Agente não retornou resposta para {operation_description} (file: {effective_filename})")
            raise HTTPException(status_code=500, detail="Agente não retornou os detalhes completos do plano extraído.")
        
        extracted_details = json.loads(full_details_json_str)
        if "error" in extracted_details:
            error_detail = extracted_details.get('details', extracted_details.get('error', 'Erro desconhecido da ferramenta'))
            logger.error(f"Erro da ferramenta {operation_description} (file: {effective_filename}): {error_detail}")
            raise HTTPException(status_code=500, detail=f"Falha na extração dos detalhes: {error_detail}")

        return FullPlanDetailsResponse(
            stored_markdown_id=stored_doc_id,
            user_id=user_id,
            thread_id=thread_id, # Retorna o thread_id da conversa original
            original_pdf_filename=effective_filename,
            nomeCurso=extracted_details.get("nomeCurso"),
            unidadesCurriculares=extracted_details.get("unidadesCurriculares", [])
        )

    except HTTPException as he:
        # Log e re-raise HTTPExceptions
        logger.error(f"HTTPException no endpoint {operation_description} (file: {effective_filename}): {he.detail}", exc_info=not isinstance(he.detail, str) or "File not found" not in he.detail) # Evita stacktrace para file not found comum
        raise he
    except ValueError as ve: # Ex: GCS bucket não configurado no document_store
        logger.error(f"ValueError no endpoint {operation_description} (file: {effective_filename}): {str(ve)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(ve)) # Pode ser um erro de configuração
    except Exception as e:
        logger.error(f"Erro inesperado em /{operation_description} (file: {effective_filename}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar PDF para detalhes completos: {str(e)}")

@app.post("/teaching_plan/generate", response_model=PlanGenerationResponse)
async def generate_teaching_plan( # Nome do endpoint corrigido
    body: PlanGenerationBodyWithStoredId # Usa o modelo de corpo de requisição atualizado
):
    operation_description = "generate_teaching_plan"
    logger.info(f"Endpoint /{operation_description} chamado para stored_id: {body.stored_markdown_id} por user: {body.user_id}, thread_orig: {body.thread_id}")

    # Usar o thread_id da conversa principal
    agent_interaction_thread_id = body.thread_id
    
    horarios_list_of_dicts = [h.model_dump() for h in body.horarios] if body.horarios else []

    # Preparar o payload inicial para o agente
    agent_initial_payload = {
        "user_id": body.user_id,
        "thread_id": agent_interaction_thread_id,
        "stored_markdown_id": body.stored_markdown_id,
        "plan_docente": body.docente,
        "plan_unidade_operacional": body.escola, # Mapeamento de 'escola' para 'unidade_operacional'
        "plan_nome_curso": body.curso,           # Mapeamento de 'curso' para 'plan_nome_curso'
        "plan_nome_uc": body.uc,               # Mapeamento de 'uc' para 'plan_nome_uc'
        "plan_capacidades_tecnicas": body.capacidadesTecnicas or [],
        "plan_capacidades_socioemocionais": body.capacidadesSocioemocionais or [],
        "plan_estrategia": body.estrategia,
        "plan_tematica": body.tematica,
        "plan_horarios": horarios_list_of_dicts,
    }
    
    try:
        agent_result_dict = await run_agent(
            input_command_or_message=f"CMD_GENERATE_TEACHING_PLAN:doc_id={body.stored_markdown_id}", # Comando gatilho
            user_id=body.user_id,
            thread_id=agent_interaction_thread_id,
            initial_payload=agent_initial_payload
        )

        plan_markdown_json_str = agent_result_dict.get("response")
        if not plan_markdown_json_str:
            logger.error(f"Agente não retornou resposta para {operation_description} (stored_id: {body.stored_markdown_id})")
            raise HTTPException(status_code=500, detail="Agente não retornou o plano de ensino gerado.")
            
        plan_data = json.loads(plan_markdown_json_str)
        if "error" in plan_data:
            error_detail = plan_data.get('details', plan_data.get('error', 'Erro desconhecido da ferramenta'))
            logger.error(f"Erro da ferramenta {operation_description} (stored_id: {body.stored_markdown_id}): {error_detail}")
            raise HTTPException(status_code=500, detail=f"Falha na geração do plano: {error_detail}")

        return PlanGenerationResponse(
            userId=body.user_id,
            threadId=body.thread_id, # Retorna o thread_id da conversa original associada
            plan_markdown=plan_data.get("plan_markdown", "Erro: Plano não gerado ou markdown ausente na resposta.")
        )
    except HTTPException as he:
        logger.error(f"HTTPException no endpoint {operation_description} (stored_id: {body.stored_markdown_id}): {he.detail}", exc_info= not isinstance(he.detail, str) or "File not found" not in he.detail)
        raise he
    except Exception as e:
        logger.error(f"Erro inesperado em /{operation_description} (stored_id: {body.stored_markdown_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar plano de ensino: {str(e)}")
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT')), timeout_keep_alive=300)