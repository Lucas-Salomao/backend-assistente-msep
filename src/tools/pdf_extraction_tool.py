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
        system_instruction="""Você é um assistente eficiente em extrair informações específicas de textos. Responda apenas com a informação solicitada, de forma concisa e nada mais.""",
    )
    
def sanitize_text(text: str) -> str:
    if not text:
        return ""

    # 1. Escapar backslashes PRIMEIRO
    text = text.replace('\\', '\\\\')
    # 2. Escapar aspas duplas
    text = text.replace('"', '\\"')
    # 3. Substituir quebras de linha literais por espaço (ou por \\n se quiser mantê-las no JSON)
    #    Se você quer que a quebra de linha seja parte do valor da string no JSON:
    #    text = text.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
    #    Se você quer remover as quebras de linha e substituí-las por espaço:
    text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')

    text = text.strip() # Remover espaços no início/fim após as substituições

    # Remove múltiplos espaços que podem ter sido introduzidos
    while '  ' in text:
        text = text.replace('  ', ' ')

    # Opcional: Remover outros caracteres de controle problemáticos,
    # mas os acima são os mais críticos para JSON strings.
    # A linha abaixo pode ser muito agressiva, vamos testar sem ela primeiro se as escapes resolverem.
    # text = ''.join(char for char in text if ord(char) >= 32 or char in ['\\t']) # Permitir tab escapado se necessário

    return text

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
- Retorne apenas as capacidades na íntegra como aparecem no plano de curso, uma por linha.
- Devido a conversão do plano de pdf para markdown, uma capacidade pode estar dividida em várias linhas, então traga a frase completa da capacidade em uma única linha.
- Não use marcadores, números ou símbolos.

Capacidades técnicas:"""

        response_tec = await llm.generate_content_async(prompt_tec)
        if response_tec and response_tec.text:
            raw_capabilities = [sanitize_text(cap.strip()) for cap in response_tec.text.splitlines() if cap.strip()]
            cap_details["CapacidadesTecnicas_list"] = [cap for cap in raw_capabilities if cap]

        # Prompt para capacidades socioemocionais
        prompt_soc = f"""{markdown_content}

Extraia APENAS as capacidades socioemocionais da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas as capacidades na íntegra como aparecem no plano de curso, uma por linha.
- Devido a conversão do plano de pdf para markdown, uma capacidade pode estar dividida em várias linhas, então traga a frase completa da capacidade em uma única linha.
- Não use marcadores, números ou símbolos.

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

async def _extract_knowledge_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> List[str]:
    """Função auxiliar para extrair conhecimentos de uma única UC."""
    logger.debug(f"Extraindo conhecimentos para UC: {uc_name}")
    knowledge_list: List[str] = []

    try:
        prompt_knowledge = f"""{markdown_content}

Extraia APENAS a lista de conhecimentos da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas os conhecimentos na íntegra como aparecem no plano de curso, um por linha.
- Não use marcadores complexos, números de lista são aceitáveis se fizerem parte do texto original dos conhecimentos.
- Se os conhecimentos estiverem em tópicos e sub-tópicos, tente manter essa estrutura da melhor forma possível, mas cada item principal ou sub-item em uma nova linha.

Conhecimentos:"""

        response_knowledge = await llm.generate_content_async(prompt_knowledge)
        if response_knowledge and response_knowledge.text:
            raw_knowledge = [sanitize_text(k.strip()) for k in response_knowledge.text.splitlines() if k.strip()]
            knowledge_list = [k for k in raw_knowledge if k] # Remove linhas vazias após sanitização

        logger.debug(f"Conhecimentos extraídos para {uc_name}: {len(knowledge_list)} itens.")

    except Exception as e:
        logger.error(f"Erro ao extrair conhecimentos para UC '{uc_name}': {e}")
        # Retorna lista vazia em caso de erro

    return knowledge_list

async def _extract_objective_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> Optional[str]:
    """Função auxiliar para extrair o objetivo de uma única UC."""
    logger.debug(f"Extraindo objetivo para UC: {uc_name}")
    objective: Optional[str] = None

    try:
        prompt_objective = f"""{markdown_content}

Extraia APENAS o objetivo principal ou geral da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas o texto do objetivo da unidade curricular na íntegra, sem modificações.

Objetivo da Unidade Curricular '{uc_name}':"""

        response_objective = await llm.generate_content_async(prompt_objective)
        if response_objective and response_objective.text:
            objective_text = sanitize_text(response_objective.text.strip())
            if objective_text: # Garante que não seja uma string vazia após sanitização
                objective = objective_text

        logger.debug(f"Objetivo extraído para {uc_name}: {'Sim' if objective else 'Não encontrado'}")

    except Exception as e:
        logger.error(f"Erro ao extrair objetivo para UC '{uc_name}': {e}")
        # Retorna None em caso de erro

    return objective

async def _extract_references_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> List[str]:
    """Função auxiliar para extrair referências bibliográficas de uma única UC."""
    logger.debug(f"Extraindo referências bibliográficas para UC: {uc_name}")
    references_list: List[str] = []

    try:
        prompt_references = f"""{markdown_content}

Extraia APENAS a lista de referências bibliográficas (básicas e complementares, se houver) da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas as referências, uma por linha.
- Não use marcadores, números ou símbolos.

Referências Bibliográficas da Unidade Curricular '{uc_name}':"""

        response_references = await llm.generate_content_async(prompt_references)
        if response_references and response_references.text:
            raw_references = [sanitize_text(ref.strip()) for ref in response_references.text.splitlines() if ref.strip()]
            references_list = [ref for ref in raw_references if ref] # Remove linhas vazias após sanitização

        logger.debug(f"Referências bibliográficas extraídas para {uc_name}: {len(references_list)} itens.")

    except Exception as e:
        logger.error(f"Erro ao extrair referências para UC '{uc_name}': {e}")
        # Retorna lista vazia em caso de erro

    return references_list

async def _extract_workload_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> List[str]:
    """Função auxiliar para extrair a carga horária total de uma única UC."""
    logger.debug(f"Extraindo carga horária para UC: {uc_name}")
    workload: str = ""

    try:
        prompt_workload = f"""{markdown_content}

Extraia APENAS a carga horária total em horas da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas a carga horaria total em horas, sem explicações adicionais.
- Não use marcadores, números ou símbolos.

Carga horária total '{uc_name}':"""

        response_workload = await llm.generate_content_async(prompt_workload)
        if response_workload:
            workload = sanitize_text(response_workload.text.strip())

        logger.debug(f"Carga horária total extraídas para {uc_name}: {workload} horas.")

    except Exception as e:
        logger.error(f"Erro ao extrair carga horária para UC '{uc_name}': {e}")

    return workload

async def _extract_module_for_single_uc(llm: genai.GenerativeModel, markdown_content: str, uc_name: str) -> List[str]:
    """Função auxiliar para extrair o tipo de módulo de uma única UC."""
    logger.debug(f"Extraindo o tipo de módulo: {uc_name}")
    module: str = ""

    try:
        prompt_module = f"""{markdown_content}

Extraia APENAS o tipo de módulo (básico, específico, etc) da Unidade Curricular '{uc_name}'.

INSTRUÇÕES IMPORTANTES:
- Retorne apenas o tipo de módulo da unidade curricular, sem explicações adicionais.
- Não use marcadores, números ou símbolos.

Módulo da UC '{uc_name}':"""

        response_module = await llm.generate_content_async(prompt_module)
        if response_module and response_module.text:
            module = sanitize_text(response_module.text.strip())

        logger.debug(f"Tipo de módulo extraído para {uc_name}: {module}.")

    except Exception as e:
        logger.error(f"Erro ao extrair tipo de módulo para UC '{uc_name}': {e}")

    return module

@tool
async def extract_full_plan_details(markdown_content: str) -> str:
    """
    Extrai o nome do curso, lista de UCs, e para cada UC, suas capacidades, 
    conhecimentos, objetivo e referências bibliográficas a partir de um conteúdo Markdown.
    Retorna uma string JSON com todos os dados agregados.
    """
    logger.info("Tool: extract_full_plan_details (com objetivo e refs) chamada.")
    if not markdown_content:
        logger.warning("Conteúdo Markdown não fornecido para extração completa.")
        return json.dumps({"error": "Conteúdo Markdown não fornecido."}, ensure_ascii=False, indent=2)

    results: Dict[str, Any] = {
        "nomeCurso": None,
        "modalidade": None,
        "unidadesCurriculares": []
    }

    try:
        llm = await get_extraction_llm()

        # Etapa A: Extrair nome do curso (como antes)
        prompt_nome_curso = f"""{markdown_content}

Extraia o nome completo do curso descrito neste documento.
INSTRUÇÕES:
- Retorne somente o nome do curso.
- Não inclua explicações ou texto adicional.
Nome do curso:"""
        response_nome_curso = await llm.generate_content_async(prompt_nome_curso)
        if response_nome_curso and response_nome_curso.text:
            results["nomeCurso"] = sanitize_text(response_nome_curso.text.strip())
            logger.info(f"Nome do curso extraído: {results['nomeCurso']}")

        # Etapa B: Extrair a modalidade de ensino
        prompt_modalidade = f"""{markdown_content}

Extraia a modalidade de ensino(presencial, híbrida ou EAD) do curso descrito neste documento.
INSTRUÇÕES:
- Retorne somente a modalidade de ensino.
- Não inclua explicações ou texto adicional.
Modalidade de Ensino:"""
        response_modalidade = await llm.generate_content_async(prompt_modalidade)
        if response_modalidade and response_modalidade.text:
            results["modalidade"] = sanitize_text(response_modalidade.text.strip())
            logger.info(f"Modalidade de Ensino extraído: {results['modalidade']}")
        
        # Etapa C: Extrair lista de UCs (como antes)
        prompt_ucs_list = f"""{markdown_content}

Extraia todas as Unidades Curriculares (UCs) do plano de curso.
INSTRUÇÕES IMPORTANTES:
- Retorne apenas os nomes das UCs, uma por linha.
- Não use marcadores, números ou símbolos no início de cada nome de UC.
- Não inclua frases introdutórias como "As UCs são:".
Lista de Unidades Curriculares:"""
        response_ucs_list = await llm.generate_content_async(prompt_ucs_list)
        ucs_nomes = []
        if response_ucs_list and response_ucs_list.text:
            raw_ucs = [sanitize_text(uc.strip()) for uc in response_ucs_list.text.splitlines() if uc.strip()]
            ucs_nomes = [uc for uc in raw_ucs if uc] # Filtra strings vazias
            logger.info(f"UCs extraídas: {len(ucs_nomes)} unidades encontradas: {ucs_nomes}")


        # Etapa D: Para cada UC, extrair todos os detalhes
        capability_tasks = []
        knowledge_tasks = []
        objective_tasks = []
        reference_tasks = []
        workload_tasks = []
        module_tasks = []

        for uc_nome in ucs_nomes:
            if uc_nome:
                capability_tasks.append(_extract_capabilities_for_single_uc(llm, markdown_content, uc_nome))
                knowledge_tasks.append(_extract_knowledge_for_single_uc(llm, markdown_content, uc_nome))
                objective_tasks.append(_extract_objective_for_single_uc(llm, markdown_content, uc_nome))
                reference_tasks.append(_extract_references_for_single_uc(llm, markdown_content, uc_nome))
                workload_tasks.append(_extract_workload_for_single_uc(llm, markdown_content, uc_nome))
                module_tasks.append(_extract_module_for_single_uc(llm, markdown_content, uc_nome))

        # Executar todas as tarefas de extração em paralelo
        # (capacidades_results, conhecimentos_results, objetivos_results, referencias_results) = await asyncio.gather(
        #     asyncio.gather(*capability_tasks) if capability_tasks else asyncio.sleep(0, result=[]), # type: ignore
        #     asyncio.gather(*knowledge_tasks) if knowledge_tasks else asyncio.sleep(0, result=[]), # type: ignore
        #     asyncio.gather(*objective_tasks) if objective_tasks else asyncio.sleep(0, result=[]), # type: ignore
        #     asyncio.gather(*reference_tasks) if reference_tasks else asyncio.sleep(0, result=[]), # type: ignore
        # )
        # Simplificando o gather:
        all_gathered_results = []
        if ucs_nomes: # Só executa gather se houver UCs
            tasks_to_run = []
            for uc_nome_idx in range(len(ucs_nomes)):
                 # Para cada UC, agrupamos suas 4 tarefas de extração
                if ucs_nomes[uc_nome_idx]: # Checa se o nome da UC não é vazio
                    tasks_to_run.append(
                        asyncio.gather(
                            capability_tasks[uc_nome_idx],
                            knowledge_tasks[uc_nome_idx],
                            objective_tasks[uc_nome_idx],
                            reference_tasks[uc_nome_idx],
                            workload_tasks[uc_nome_idx],
                            module_tasks[uc_nome_idx]
                        )
                    )
            if tasks_to_run:
                logger.info(f"Iniciando extração detalhada para {len(tasks_to_run)} UCs...")
                all_gathered_results = await asyncio.gather(*tasks_to_run)
                logger.info("Extração detalhada de todas as UCs concluída.")


        # Montar o resultado final
        for i, uc_nome in enumerate(ucs_nomes):
            if uc_nome and i < len(all_gathered_results):
                # all_gathered_results[i] será uma tupla: (caps_dict, knowledge_list, objective_str, refs_list)
                uc_capabilities, uc_knowledge, uc_objective, uc_references, uc_workload, uc_module = all_gathered_results[i]

                results["unidadesCurriculares"].append({
                    "nomeUC": uc_nome,
                    "tipoModulo": uc_module if uc_module else None,
                    "carga_horaria_total": uc_workload if uc_workload else None,
                    "objetivo_uc": uc_objective if uc_objective else None,
                    "carga_horaria_total": uc_workload if uc_workload else None,
                    "capacidades": uc_capabilities if uc_capabilities else {"CapacidadesTecnicas_list": [], "CapacidadesSocioemocionais_list": []},
                    "conhecimentos": uc_knowledge if uc_knowledge else [],
                    "referencias_bibliograficas": uc_references if uc_references else []
                })

        logger.info(f"Extração completa finalizada: {len(results['unidadesCurriculares'])} UCs processadas.")

        json_result = json.dumps(results, ensure_ascii=False, indent=2, separators=(',', ': '))

        try:
            json.loads(json_result)
            logger.info("JSON de extração completada sucesso.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido gerado pela extração completa: {e}. Conteúdo (início): {json_result}")
            return json.dumps({"error": f"Erro na serialização JSON da extração: {str(e)}"}, ensure_ascii=False)
        return json_result

    except Exception as e:
        logger.error(f"Erro em extract_full_plan_details (com objetivo e refs): {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao extrair detalhes completos do plano: {str(e)}"}, ensure_ascii=False)
