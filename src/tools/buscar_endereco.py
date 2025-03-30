from langchain_core.tools import tool
import requests
import json
import logging

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
def buscar_endereco(localidade: str):
    """Busca o endereço de uma localidade e retorna o endereço formatado junto com o embed do Google Maps.
    
    Args:
        localidade (str): Nome da localidade a ser buscada.
    
    Returns:
        str: Endereço formatado e embed do Google Maps.
    """
    try:
        logging.info('Endpoint buscar endereco acessado')
        # Obter as coordenadas da localidade
        latitude, longitude = get_coordinates(localidade)
        
        # Gerar o embed do Google Maps
        embed_html = generate_google_maps_embed(latitude, longitude)
        
        # Obter o endereço formatado
        endereco = get_formatted_address(localidade)
        
        # Criar um dicionário com os dados
        resultado = {
            "endereco": endereco,
            "mapa": embed_html
        }
        
        # Converter o dicionário para JSON
        resultado_json = json.dumps(resultado, ensure_ascii=False)
        
        # print(f"Endereço: {endereco}\n\nMapa:\n{embed_html}")
        # # Retornar o endereço e o embed do mapa
        # return f"Endereço: {endereco}\n\nMapa:\n{embed_html}"
        
        # Retornar o JSON
        return resultado_json
    
    except Exception as e:
        logging.error(f"Erro ao buscar endereço: {e}")
        # return f"Erro ao buscar endereço: {str(e)}"
        return json.dumps({"error": str(e)})
    
# Função para obter o endereço formatado
def get_formatted_address(location_name):
    api_key = "AIza@@@SyBwTq!!!!noyMZ!!!!S0FSQ@@@@Ltg!!!!!MSeC6F0d@@@8TAZ!!!1Uq4"
    api_key_limpa = api_key.replace('@', '').replace('!', '')
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={api_key_limpa}"
    response = requests.get(url).json()
    
    if response['status'] == 'OK':
        return response['results'][0]['formatted_address']
    else:
        raise Exception("Localidade não encontrada")

# Função para gerar o embed do Google Maps
def generate_google_maps_embed(latitude, longitude):
    api_key = "AIza@@@SyBwTq!!!!noyMZ!!!!S0FSQ@@@@Ltg!!!!!MSeC6F0d@@@8TAZ!!!1Uq4"
    api_key_limpa = api_key.replace('@', '').replace('!', '')
    embed_html = f"""
    <iframe
        width="100%"
        height="450"
        frameborder="0" style="border:0"
        src="https://www.google.com/maps/embed/v1/place?key={api_key_limpa}&q={latitude},{longitude}"
        allowfullscreen>
    </iframe>
    """
    return embed_html

# Função para obter as coordenadas de uma localidade
def get_coordinates(location_name):
    api_key = "AIza@@@SyBwTq!!!!noyMZ!!!!S0FSQ@@@@Ltg!!!!!MSeC6F0d@@@8TAZ!!!1Uq4"
    api_key_limpa = api_key.replace('@', '').replace('!', '')
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={api_key_limpa}"
    response = requests.get(url).json()
    
    if response['status'] == 'OK':
        location = response['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        raise Exception("Localidade não encontrada")
    
tool = buscar_endereco