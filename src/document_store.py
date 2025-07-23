import os
import logging
import uuid
import asyncio
from typing import Optional, Dict, Any
from psycopg import AsyncConnection
from google.cloud import storage
from google.api_core.exceptions import NotFound

logger = logging.getLogger(__name__)

# Configurações
STRING_POSTGRES = f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
GCS_MARKDOWN_BUCKET_NAME = os.getenv("GCS_MARKDOWN_BUCKET_NAME")
GCS_PLANS_BUCKET_NAME = os.getenv("GCS_PLANS_BUCKET_NAME")

async def get_db_connection():
    return await AsyncConnection.connect(STRING_POSTGRES, autocommit=True)

async def init_document_table():
    """Cria a tabela 'processed_documents' se ela não existir.
    O conteúdo Markdown será SEMPRE armazenado no GCS."""
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_documents (
                    id UUID PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    thread_id VARCHAR(255) NOT NULL,
                    original_pdf_filename VARCHAR(512),
                    gcs_blob_name VARCHAR(1024) NOT NULL, -- Caminho para o arquivo no GCS
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_processed_documents_user_id ON processed_documents (user_id);")
            await cur.execute("CREATE INDEX IF NOT EXISTS idx_processed_documents_thread_id ON processed_documents (thread_id);")
            logger.info("Tabela 'processed_documents' (GCS only) verificada/criada com sucesso.")

async def _upload_to_gcs(bucket_name: str, content: str, blob_name: str) -> None:
    if not bucket_name:
        raise ValueError("Nome do bucket GCS não configurado.")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        await asyncio.to_thread(blob.upload_from_string, content, content_type='text/markdown')
        logger.info(f"Conteúdo Markdown enviado para GCS: gs://{bucket_name}/{blob_name}")
    except Exception as e:
        logger.error(f"Erro ao enviar para GCS (gs://{bucket_name}/{blob_name}): {e}", exc_info=True)
        raise

async def _download_from_gcs(bucket_name: str, blob_name: str) -> Optional[str]:
    if not bucket_name:
        raise ValueError("Nome do bucket GCS não configurado.")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        exists = await asyncio.to_thread(blob.exists)
        if not exists:
            logger.warning(f"Blob GCS não encontrado: gs://{bucket_name}/{blob_name}")
            return None
        
        content_bytes = await asyncio.to_thread(blob.download_as_bytes)
        logger.info(f"Conteúdo Markdown baixado de GCS: gs://{bucket_name}/{blob_name}")
        return content_bytes.decode('utf-8')
    except NotFound:
        logger.warning(f"Blob GCS não encontrado (NotFound): gs://{bucket_name}/{blob_name}")
        return None
    except Exception as e:
        logger.error(f"Erro ao baixar de GCS (gs://{bucket_name}/{blob_name}): {e}", exc_info=True)
        raise

async def store_markdown_document(
    user_id: str,
    thread_id: str,
    markdown_content: str,
    original_pdf_filename: Optional[str] = None
) -> str:
    """
    Armazena o conteúdo Markdown SEMPRE no GCS e os metadados no DB.
    Retorna o ID do documento armazenado (para o registro no DB).
    """
    doc_id = uuid.uuid4()
    
    if not GCS_MARKDOWN_BUCKET_NAME:
        logger.error("GCS Bucket não configurado. Não é possível armazenar o Markdown.")
        raise ValueError("GCS Bucket não configurado para armazenar arquivo.")

    gcs_blob_name = f"processed_markdowns/{user_id}/{doc_id}.json" # Padrão de nomeação no GCS
    
    await _upload_to_gcs(GCS_MARKDOWN_BUCKET_NAME, markdown_content, gcs_blob_name)
    logger.info(f"Markdown (ID: {doc_id}) armazenado no GCS em {gcs_blob_name}.")

    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO processed_documents 
                (id, user_id, thread_id, original_pdf_filename, gcs_blob_name)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (doc_id, user_id, thread_id, original_pdf_filename, gcs_blob_name)
            )
    logger.info(f"Metadados do Markdown (ID: {doc_id}, GCS: {gcs_blob_name}) salvos no DB.")
    return str(doc_id)

async def store_plan_document(
    user_id: str,
    thread_id: str,
    plan_json_content: str,
    course_plan_id: str,
) -> str:
    """
    Armazena o plano de curso (JSON) no GCS e os metadados na tabela user_plans.
    Retorna o ID do plano armazenado.
    """
    plan_id = uuid.uuid4()

    if not GCS_PLANS_BUCKET_NAME:
        logger.error("GCS Bucket não configurado. Não é possível armazenar o plano.")
        raise ValueError("GCS Bucket não configurado para armazenar arquivo.")

    gcs_blob_name = f"user_plans/{user_id}/{plan_id}.json"

    await _upload_to_gcs(GCS_PLANS_BUCKET_NAME, plan_json_content, gcs_blob_name)
    logger.info(f"Plano (ID: {plan_id}) armazenado no GCS em {gcs_blob_name}.")

    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_plans 
                (id, user_id, thread_id, course_plan_id, gcs_blob_name)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (plan_id, user_id, thread_id, course_plan_id, gcs_blob_name)
            )
    logger.info(f"Metadados do plano (ID: {plan_id}, GCS: {gcs_blob_name}) salvos no DB.")
    return str(plan_id)

async def get_markdown_document(stored_doc_id: str) -> Optional[str]:
    """Recupera o conteúdo Markdown do GCS usando o ID do registro no DB."""
    try:
        doc_uuid = uuid.UUID(stored_doc_id)
    except ValueError:
        logger.error(f"ID de documento inválido fornecido para recuperação: {stored_doc_id}")
        return None

    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT gcs_blob_name FROM processed_documents WHERE id = %s",
                (doc_uuid,)
            )
            record = await cur.fetchone()

    if not record:
        logger.warning(f"Nenhum documento encontrado com ID: {stored_doc_id}")
        return None

    gcs_blob_name = record[0]
    if not gcs_blob_name:
        logger.error(f"Registro do DB para ID: {stored_doc_id} não tem gcs_blob_name (deveria ter).")
        return None
        
    logger.info(f"Markdown (ID: {stored_doc_id}) será recuperado do GCS path: {gcs_blob_name}.")
    return await _download_from_gcs(GCS_MARKDOWN_BUCKET_NAME, gcs_blob_name)

async def setup_document_storage():
    await init_document_table()
    if not GCS_MARKDOWN_BUCKET_NAME:
        logger.critical("GCS_MARKDOWN_BUCKET_NAME NÃO ESTÁ DEFINIDO. O ARMAZENAMENTO DE MARKDOWN NÃO FUNCIONARÁ.")
        raise EnvironmentError("GCS_MARKDOWN_BUCKET_NAME não está configurado.")
    else:
        logger.info(f"Armazenamento GCS configurado para usar o bucket: {GCS_MARKDOWN_BUCKET_NAME}")
        
async def get_plan_document(plan_id: str) -> Optional[str]:
    """Recupera o conteúdo JSON de um plano específico do GCS usando o seu ID."""
    try:
        # Valida se o ID tem o formato de um UUID
        plan_uuid = uuid.UUID(plan_id)
    except ValueError:
        logger.error(f"ID de plano inválido fornecido para recuperação: {plan_id}")
        return None

    # Conecta ao DB para encontrar o caminho do arquivo no GCS
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT gcs_blob_name FROM user_plans WHERE id = %s",
                (plan_uuid,)
            )
            record = await cur.fetchone()

    if not record:
        logger.warning(f"Nenhum plano encontrado com ID: {plan_id}")
        return None

    gcs_blob_name = record[0]
    if not gcs_blob_name:
        logger.error(f"Registro do DB para o plano ID: {plan_id} não possui um caminho GCS (gcs_blob_name).")
        return None
        
    logger.info(f"Plano (ID: {plan_id}) será recuperado do GCS path: {gcs_blob_name}.")
    
    # Usa a função auxiliar existente para baixar o conteúdo do GCS
    return await _download_from_gcs(GCS_PLANS_BUCKET_NAME, gcs_blob_name)
