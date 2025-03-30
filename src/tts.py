from google.cloud import texttospeech
import logging
import os
import re
from dotenv import load_dotenv
import tempfile2
import asyncio

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

async def remove_markdown(text):
    """
    Remove formatação markdown e retorna texto puro.
    """
    # Remove links no formato [texto](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove links no formato <url>
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove formatação de código
    text = re.sub(r'`{1,3}[^`]*`{1,3}', lambda m: m.group(0).replace('`', ''), text)
    
    # Remove headers
    text = re.sub(r'^\#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove negrito e itálico
    text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    
    # Remove listas
    text = re.sub(r'^\s*[\-\*\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove blockquotes
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    
    # Remove linhas horizontais
    text = re.sub(r'^\s*[\*\-_]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # Remove espaços extras e linhas em branco múltiplas
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

async def prepare_for_tts(markdown_text):
    """
    Prepara texto markdown para TTS:
    1. Remove formatação markdown
    2. Ajusta pontuação e espaçamento para melhor resultado no TTS
    """
    # Remove markdown
    text = await remove_markdown(markdown_text)
    
    # Adiciona pausa após pontuação
    text = re.sub(r'([.!?])\s+', r'\1\n', text)
    
    # Remove caracteres especiais que podem afetar o TTS
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text

async def text_to_speach(message:str)-> str:           
    """Gera um arquivo de áudio MP3 a partir do texto usando Google Text-to-Speech."""
    try:
        # Instancia o cliente do Google TTS
        client = texttospeech.TextToSpeechClient()

        # Prepara o texto
        prepared_text = await prepare_for_tts(message)
        if not prepared_text:
            raise ValueError("Nenhum texto fornecido para síntese")

        # Configura a entrada de texto
        synthesis_input = texttospeech.SynthesisInput(text=prepared_text)

        # Configura a voz
        voice = texttospeech.VoiceSelectionParams(
            language_code="pt-BR",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
            name="pt-BR-Standard-C"
        )

        # Configura o áudio
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=5.0
        )

        # Faz a requisição de síntese de voz
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Cria um arquivo temporário
        with tempfile2.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(response.audio_content)
            temp_file.flush()
            temp_file_path = temp_file.name

        logger.info(f"Áudio gerado com sucesso: {temp_file_path}")
        return temp_file_path

    except Exception as e:
        logger.error(f"Erro ao gerar áudio TTS: {str(e)}")
        raise