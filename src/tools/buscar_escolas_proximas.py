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

api_key = "AIza@@@SyBwTq!!!!noyMZ!!!!S0FSQ@@@@Ltg!!!!!MSeC6F0d@@@8TAZ!!!1Uq4"
api_key_limpa = api_key.replace('@', '').replace('!', '')
        
@tool
def buscar_escolas_proximas(latitude: str, longitude: str):
    """
    Busca escolas SENAI próximas à localização fornecida e retorna o código HTML para exibir um mapa com marcadores das escolas,
    incluindo telefone, site, foto e endereço.

    Args:
        latitude (float): Latitude da localização do usuário.
        longitude (float): Longitude da localização do usuário.

    Returns:
        str: Código HTML contendo o mapa e as informações detalhadas das escolas.
    """
    try:
        logging.info('Endpoint buscar_escolas_proximas acessado')
        
        

        # Busca escolas SENAI próximas usando a API do Google Places
        endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': 'Escola SENAI',
            'location': f'{latitude},{longitude}',
            'key': api_key_limpa
        }
        response = requests.get(endpoint, params=params)
        schools = response.json().get('results', [])[:4]

        # Adiciona detalhes extras para cada escola
        for school in schools:
            details = get_place_details(school['place_id'])
            if 'result' in details:
                school['phone'] = details['result'].get('formatted_phone_number', 'Não disponível')
                school['website'] = details['result'].get('website', 'Não disponível')
                if 'photos' in details['result']:
                    photo_reference = details['result']['photos'][0]['photo_reference']
                    school['photo_url'] = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={api_key_limpa}"
                else:
                    school['photo_url'] = None
                school['rating'] = details['result'].get('rating', 'N/A')
                school['opening_hours'] = details['result'].get('opening_hours', {}).get('open_now', False)

        # Gerar o HTML dinamicamente
        html_content = f"""
        <div id="map" style="height: 500px; width: 100%;"></div>
        <script>
            let map;
            let infoWindow;

            function initMap() {{
                map = new google.maps.Map(document.getElementById('map'), {{
                    zoom: 13,
                    center: {{ lat: {latitude}, lng: {longitude} }}
                }});

                infoWindow = new google.maps.InfoWindow({{
                    maxWidth: 320
                }});

                // Marcador da localização do usuário
                new google.maps.Marker({{
                    position: {{ lat: {latitude}, lng: {longitude} }},
                    map: map,
                    title: "Sua localização",
                    icon: {{
                        url: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
                    }}
                }});

                // Marcadores das escolas
                {json.dumps(schools)}.forEach(school => {{
                    const marker = new google.maps.Marker({{
                        position: {{
                            lat: school.geometry.location.lat,
                            lng: school.geometry.location.lng
                        }},
                        map: map,
                        title: school.name
                    }});

                    marker.addListener("click", () => {{
                        const content = `
                            <div class="school-info">
                                <h3>${{school.name}}</h3>
                                ${{school.photo_url ? `<img src="${{school.photo_url}}" alt="${{school.name}}">` : ''}}
                                <p><strong>Endereço:</strong><br>${{school.formatted_address}}</p>
                                <p><strong>Telefone:</strong><br>${{school.phone || 'Não disponível'}}</p>
                                ${{school.website ? `<p><strong>Website:</strong><br><a href="${{school.website}}" target="_blank">${{school.website}}</a></p>` : ''}}
                            </div>
                        `;
                        infoWindow.setContent(content);
                        infoWindow.open(map, marker);
                    }});
                }});
            }}
        </script>
        <script async defer
            src="https://maps.googleapis.com/maps/api/js?key={api_key_limpa}&callback=initMap">
        </script>
        """
        
        return json.dumps({
            "endereco": "\n".join([school["formatted_address"] for school in schools]),
            "mapa": html_content,
        }, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Erro ao buscar escolas próximas: {e}")
        return f"Erro ao buscar escolas próximas: {str(e)}"

def get_place_details(place_id):
    """
    Busca detalhes adicionais de um local específico
    """
    endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
    
    params = {
        'place_id': place_id,
        'fields': 'name,formatted_phone_number,website,photos,formatted_address,',
        'key': api_key_limpa
    }
    
    response = requests.get(endpoint, params=params)
    return response.json()

tool = buscar_escolas_proximas