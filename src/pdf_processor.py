import logging
import tempfile
import os
import asyncio
from fastapi import UploadFile, HTTPException
from docling.document_converter import DocumentConverter # Certifique-se que 'docling' está no seu requirements.txt

logger = logging.getLogger(__name__)

async def convert_pdf_to_markdown(file: UploadFile) -> str:
    """
    Converte um arquivo PDF enviado para texto Markdown usando docling.
    O arquivo é salvo temporariamente para processamento.
    """
    tmp_pdf_path = None
    try:
        # Salva UploadFile em um arquivo temporário nomeado
        # delete=False é importante para que o DocumentConverter possa abri-lo pelo nome
        # e nós o removemos manualmente no bloco finally.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            content = await file.read() # Lê o conteúdo do UploadFile
            if not content:
                logger.warning(f"Arquivo PDF '{file.filename}' está vazio.")
                raise HTTPException(status_code=400, detail=f"Arquivo PDF '{file.filename}' está vazio.")
            tmp_pdf.write(content)
            tmp_pdf_path = tmp_pdf.name
        
        logger.info(f"Arquivo PDF temporário salvo em: {tmp_pdf_path} para conversão.")
        
        converter = DocumentConverter()
        
        # DocumentConverter.convert() é síncrono, então rodamos em um executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, converter.convert, tmp_pdf_path)
        # Alternativamente, se sua versão do docling ou contexto permitir,
        # e se .convert for CPU-bound, o executor é bom. Se for I/O-bound e tiver async nativo, melhor.
        
        if result and result.document:
            markdown_text = result.document.export_to_markdown()
            if not markdown_text.strip(): # Verifica se o markdown resultante não é apenas espaços em branco
                logger.warning(f"Markdown extraído do PDF '{file.filename}' está vazio ou contém apenas espaços.")
                # Pode ser um PDF de imagem sem OCR, ou um PDF malformado.
                raise HTTPException(status_code=400, detail="Não foi possível extrair conteúdo textual do PDF. O PDF pode ser uma imagem ou estar corrompido.")
            logger.info(f"PDF '{file.filename}' convertido para Markdown com sucesso (tamanho: {len(markdown_text)}).")
            return markdown_text
        else:
            logger.error(f"Falha ao converter PDF '{file.filename}'. Resultado do docling: {result}")
            raise HTTPException(status_code=500, detail="Falha ao converter PDF para Markdown usando a biblioteca docling.")

    except HTTPException as he: # Repassa HTTPExceptions já tratadas
            raise he
    except Exception as e:
        logger.error(f"Erro durante a conversão de PDF para Markdown ('{file.filename}'): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro inesperado ao converter PDF: {str(e)}")
    finally:
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            try:
                os.remove(tmp_pdf_path)
                logger.info(f"Arquivo PDF temporário '{tmp_pdf_path}' removido.")
            except Exception as e_remove:
                logger.error(f"Erro ao remover arquivo PDF temporário '{tmp_pdf_path}': {e_remove}", exc_info=True)
        if file: # Garante que o arquivo seja fechado se foi aberto pelo FastAPI
             # O FastAPI geralmente lida com o fechamento do UploadFile,
             # mas uma chamada explícita após a leitura pode ser uma boa prática em alguns cenários.
             # No entanto, 'await file.read()' já consumiu o stream.
             pass # await file.close() # Pode não ser necessário ou causar erro se já fechado.