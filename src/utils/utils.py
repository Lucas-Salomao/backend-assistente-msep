import logging
import os


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