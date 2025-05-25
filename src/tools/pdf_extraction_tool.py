import logging
import json
import os
from typing import Optional, List, Dict, Any # Adicionado Dict, Any
from langchain_core.tools import tool
import google.generativeai as genai # Ou sua forma preferida de acessar o LLM
import asyncio # Para chamadas concorrentes ao LLM para capacidades

logger = logging.getLogger(__name__)

# Função get_extraction_llm (como definida antes)
async def get_extraction_llm(model_name: str = os.getenv("MODEL_ID"), temperature: float = 0.1):
    generation_config_dict = {
        "temperature": temperature, "top_p": 0.95, "max_output_tokens": 8192, # Aumentado para flash
        "response_mime_type": "text/plain",
    }
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config_dict,
        system_instruction="""Você é um assistente eficiente em extrair informações específicas de textos. 
Responda apenas com a informação solicitada, de forma concisa e nada mais.
IMPORTANTE: Use apenas caracteres ASCII simples ou caracteres acentuados normais do português. 
Evite caracteres especiais que possam causar problemas de codificação.""",
    )
    
def sanitize_text(text: str) -> str:
    """Remove ou substitui caracteres problemáticos que podem quebrar o JSON."""
    if not text:
        return ""
    
    # Remove quebras de linha desnecessárias e espaços extras
    text = text.strip().replace('\n', ' ').replace('\r', ' ')
    
    # Remove múltiplos espaços
    while '  ' in text:
        text = text.replace('  ', ' ')
    
    # Remove caracteres de controle problemáticos
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    return text

# async def _extract_capabilities_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> Dict[str, List[str]]:
#     """Função auxiliar para extrair capacidades de uma única UC."""
#     logger.debug(f"Extraindo capacidades para UC: {uc_name}")
#     cap_details = {
#         "CapacidadesTecnicas_list": [],
#         "CapacidadesSocioemocionais_list": []
#     }
#     try:
#         prompt_tec = markdown_content + f"\n\nListe as capacidades técnicas (ou básicas) da Unidade Curricular '{uc_name}'. Retorne apenas as capacidades, cada uma em uma nova linha, sem marcadores ou frases introdutórias. certifique-se de que todas as strings sejam válidas para JSON. Evite usar barras invertidas a menos que seja para escapes JSON padrão"
#         response_tec = await llm.generate_content_async(prompt_tec)
#         cap_details["CapacidadesTecnicas_list"] = [cap.strip() for cap in response_tec.text.splitlines() if cap.strip()]

#         prompt_soc = markdown_content + f"\n\nListe as capacidades socioemocionais da Unidade Curricular '{uc_name}'. Retorne apenas as capacidades, cada uma em uma nova linha, sem marcadores ou frases introdutórias. certifique-se de que todas as strings sejam válidas para JSON. Evite usar barras invertidas a menos que seja para escapes JSON padrão"
#         response_soc = await llm.generate_content_async(prompt_soc)
#         cap_details["CapacidadesSocioemocionais_list"] = [cap.strip() for cap in response_soc.text.splitlines() if cap.strip()]
#         logger.debug(f"Capacidades para {uc_name}: {cap_details}")
#     except Exception as e:
#         logger.error(f"Erro ao extrair capacidades para UC '{uc_name}': {e}")
#         # Retorna listas vazias ou um indicador de erro se preferir
#     return cap_details

async def _extract_capabilities_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> Dict[str, List[str]]:
    """Função auxiliar para extrair capacidades de uma única UC."""
    logger.debug(f"Extraindo capacidades para UC: {uc_name}")
    cap_details = {
        "CapacidadesTecnicas_list": [],
        "CapacidadesSocioemocionais_list": []
    }
    
    try:
        # Prompt para capacidades técnicas com instruções mais específicas
        prompt_tec = f"""{markdown_content}

Extraia APENAS as capacidades técnicas (ou básicas) da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas as capacidades, uma por linha
- Não use marcadores, números ou símbolos
- Não inclua frases introdutórias
- Use apenas texto simples em português
- Evite caracteres especiais que possam quebrar JSON

Capacidades técnicas:"""

        response_tec = await llm.generate_content_async(prompt_tec)
        if response_tec and response_tec.text:
            raw_capabilities = [sanitize_text(cap.strip()) for cap in response_tec.text.splitlines() if cap.strip()]
            cap_details["CapacidadesTecnicas_list"] = [cap for cap in raw_capabilities if cap]

        # Prompt para capacidades socioemocionais
        prompt_soc = f"""{markdown_content}

Extraia APENAS as capacidades socioemocionais da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas as capacidades, uma por linha
- Não use marcadores, números ou símbolos
- Não inclua frases introdutórias
- Use apenas texto simples em português
- Evite caracteres especiais que possam quebrar JSON

Capacidades socioemocionais:"""

        response_soc = await llm.generate_content_async(prompt_soc)
        if response_soc and response_soc.text:
            raw_capabilities = [sanitize_text(cap.strip()) for cap in response_soc.text.splitlines() if cap.strip()]
            cap_details["CapacidadesSocioemocionais_list"] = [cap for cap in raw_capabilities if cap]
            
        logger.debug(f"Capacidades extraídas para {uc_name}: {len(cap_details['CapacidadesTecnicas_list'])} técnicas, {len(cap_details['CapacidadesSocioemocionais_list'])} socioemocionais")
        
    except Exception as e:
        logger.error(f"Erro ao extrair capacidades para UC '{uc_name}': {e}")
        # Retorna listas vazias em caso de erro
    
    return cap_details


# @tool
# async def extract_full_plan_details(markdown_content: str) -> str:
#     """
#     Extrai o nome do curso, lista de todas as UCs, e para cada UC,
#     suas capacidades técnicas e socioemocionais, a partir de um conteúdo Markdown.
#     Retorna uma string JSON com todos os dados agregados.
#     """
#     logger.info("Tool: extract_full_plan_details chamada.")
#     if not markdown_content:
#         logger.warning("Conteúdo Markdown não fornecido para extração completa.")
#         return json.dumps({"error": "Conteúdo Markdown não fornecido."})

#     results: Dict[str, Any] = {
#         "nomeCurso": None,
#         "unidadesCurriculares": [] # Lista de dicts: {"nomeUC": str, "capacidades": Dict}
#     }
    
#     try:
#         llm = await get_extraction_llm(model_name=os.getenv("MODEL_ID"))

#         # Etapa A: Extrair nome do curso
#         prompt_nome_curso = markdown_content + "\n\nQual é o nome completo do curso descrito neste documento? Responda apenas o nome do curso."
#         response_nome_curso = await llm.generate_content_async(prompt_nome_curso)
#         results["nomeCurso"] = response_nome_curso.text.strip()
#         logger.info(f"Nome do curso extraído: {results['nomeCurso']}")

#         # Etapa B: Extrair lista de UCs
#         prompt_ucs_list = markdown_content + "\n\nListe todas as Unidades Curriculares (UCs) do plano de curso. Responda apenas os nomes das UCs, cada uma em uma nova linha, sem marcadores ou frases introdutórias. Certifique-se de que todas as strings sejam válidas para JSON. Evite usar barras invertidas a menos que seja para escapes JSON padrão."
#         response_ucs_list = await llm.generate_content_async(prompt_ucs_list)
#         ucs_nomes = [uc.strip() for uc in response_ucs_list.text.splitlines() if uc.strip()]
#         logger.info(f"UCs extraídas: {ucs_nomes}")

#         # Etapa C: Para cada UC, extrair capacidades (pode ser feito em paralelo)
#         # Usaremos um LLM diferente, possivelmente mais robusto para extrações detalhadas, se necessário
#         # ou o mesmo se for suficiente.
#         # llm_for_caps = await get_extraction_llm(model_name="gemini-1.5-pro-latest", temperature=0.05)
#         llm_for_caps = llm # Reutilizando o mesmo LLM para simplicidade agora

#         tasks = []
#         for uc_nome in ucs_nomes:
#             if uc_nome: # Garante que não processe nomes de UC vazios
#                 tasks.append(_extract_capabilities_for_single_uc(llm_for_caps, markdown_content, uc_nome))
        
#         capacidades_por_uc_list = []
#         if tasks:
#             capacidades_por_uc_list = await asyncio.gather(*tasks) # Executa em "paralelo"

#         for i, uc_nome in enumerate(ucs_nomes):
#             if uc_nome:
#                 results["unidadesCurriculares"].append({
#                     "nomeUC": uc_nome,
#                     "capacidades": capacidades_por_uc_list[i] if i < len(capacidades_por_uc_list) else {"CapacidadesTecnicas_list": [], "CapacidadesSocioemocionais_list": []}
#                 })
        
#         logger.info(f"Detalhes completos do plano extraídos: {results}")
#         return json.dumps(results)

#     except Exception as e:
#         logger.error(f"Erro em extract_full_plan_details: {e}", exc_info=True)
#         return json.dumps({"error": f"Falha ao extrair detalhes completos do plano: {str(e)}"})

@tool
async def extract_full_plan_details(markdown_content: str) -> str:
    """
    Extrai o nome do curso, lista de todas as UCs, e para cada UC,
    suas capacidades técnicas e socioemocionais, a partir de um conteúdo Markdown.
    Retorna uma string JSON com todos os dados agregados.
    """
    logger.info("Tool: extract_full_plan_details chamada.")
    if not markdown_content:
        logger.warning("Conteúdo Markdown não fornecido para extração completa.")
        return json.dumps({"error": "Conteúdo Markdown não fornecido."}, ensure_ascii=False, indent=2)

    results: Dict[str, Any] = {
        "nomeCurso": None,
        "unidadesCurriculares": []
    }
    
    try:
        llm = await get_extraction_llm(model_name=os.getenv("MODEL_ID"))

        # Etapa A: Extrair nome do curso
        prompt_nome_curso = f"""{markdown_content}

Extraia o nome completo do curso descrito neste documento.

INSTRUÇÕES:
- Retorne APENAS o nome do curso
- Não inclua explicações ou texto adicional
- Use apenas caracteres normais do português

Nome do curso:"""

        response_nome_curso = await llm.generate_content_async(prompt_nome_curso)
        if response_nome_curso and response_nome_curso.text:
            results["nomeCurso"] = sanitize_text(response_nome_curso.text.strip())
            logger.info(f"Nome do curso extraído: {results['nomeCurso']}")

        # Etapa B: Extrair lista de UCs
        prompt_ucs_list = f"""{markdown_content}

Extraia todas as Unidades Curriculares (UCs) do plano de curso.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas os nomes das UCs, uma por linha
- Não use marcadores, números ou símbolos
- Não inclua frases introdutórias
- Use apenas texto simples em português

Lista de Unidades Curriculares:"""

        response_ucs_list = await llm.generate_content_async(prompt_ucs_list)
        ucs_nomes = []
        if response_ucs_list and response_ucs_list.text:
            raw_ucs = [sanitize_text(uc.strip()) for uc in response_ucs_list.text.splitlines() if uc.strip()]
            ucs_nomes = [uc for uc in raw_ucs if uc]
            logger.info(f"UCs extraídas: {len(ucs_nomes)} unidades encontradas")

        # Etapa C: Para cada UC, extrair capacidades
        llm_for_caps = llm  # Reutilizando o mesmo LLM

        tasks = []
        for uc_nome in ucs_nomes:
            if uc_nome:  # Garante que não processe nomes de UC vazios
                tasks.append(_extract_capabilities_for_single_uc(llm_for_caps, markdown_content, uc_nome))
        
        capacidades_por_uc_list = []
        if tasks:
            capacidades_por_uc_list = await asyncio.gather(*tasks)

        for i, uc_nome in enumerate(ucs_nomes):
            if uc_nome:
                capacidades = capacidades_por_uc_list[i] if i < len(capacidades_por_uc_list) else {
                    "CapacidadesTecnicas_list": [], 
                    "CapacidadesSocioemocionais_list": []
                }
                
                results["unidadesCurriculares"].append({
                    "nomeUC": uc_nome,
                    "capacidades": capacidades
                })
        
        logger.info(f"Extração completa finalizada: {len(results['unidadesCurriculares'])} UCs processadas")
        
        # Serializa o JSON com configurações que evitam problemas de codificação
        json_result = json.dumps(
            results, 
            ensure_ascii=False,  # Permite caracteres unicode normais
            indent=2,            # Para melhor legibilidade
            separators=(',', ': ')  # Separadores padrão
        )
        
        # Valida se o JSON gerado é válido
        try:
            json.loads(json_result)
            logger.info("JSON validado com sucesso")
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido gerado: {e}")
            return json.dumps({"error": f"Erro na serialização JSON: {str(e)}"}, ensure_ascii=False)
        
        return json_result

    except Exception as e:
        logger.error(f"Erro em extract_full_plan_details: {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao extrair detalhes completos do plano: {str(e)}"}, ensure_ascii=False)