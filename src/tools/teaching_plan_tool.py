import logging
import json
import os
from typing import Optional, List, Any, Dict # Adicionado Dict, Any
from langchain_core.tools import tool
import google.generativeai as genai # Ou sua forma preferida de acessar o LLM
from google.generativeai.types import HarmCategory, HarmBlockThreshold # Para safety settings
from src.document_store import get_markdown_document # Para buscar o Markdown
from src.prompts import (
    modeloCabecalhoPlanoEnsino,
    modeloItem2CapacidadesSA,
    modeloItem3ConhecimentosSA,
    modeloItem4EstrategiaSA_Base,
    modeloPlanoDeEnsinoSP,
    modeloPlanoDeEnsinoEC,
    modeloPlanoDeEnsinoP,
    modeloPlanoDeEnsinoPA,
    modeloAvaliacaoAtual,
    modeloPlanoAulaAtual
)

logger = logging.getLogger(__name__)

# Função auxiliar para o LLM (pode ser movida para um utils)
async def get_plan_generation_llm(model_name: str = os.getenv('MODEL_ID'), temperature: float = 0.7):
    generation_config_dict = {
        "temperature": temperature, "top_p": 0.95, "max_output_tokens": 8192, # Max tokens para PRO
        "response_mime_type": "text/plain",
    }
    # Configurações de segurança - ajuste conforme necessário
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config_dict,
        system_instruction="Você é um especialista em educação do Senai que elabora Planos de Ensino detalhados e bem estruturados, seguindo a Metodologia SENAI de Educação Profissional (MSEP). Tome como base o conteúdo do plano de curso anexado. As instruções entre colchetes são orientações específicas para você seguir e não devem aparecer no documento final. Avalie antes de gerar o documento final.",
        safety_settings=safety_settings
    )
    
def format_horarios_for_plano_aula(horarios: List[Dict[str,str]]) -> str:
    """Formata a lista de horarios para inclusão no prompt do plano de aula."""
    if not horarios:
        return "Nenhum horário de aula específico foi fornecido. O plano de aula deve ser genérico em relação a datas e horários."
    
    texto_horarios = "Os encontros previstos são:\n"
    for i, horario in enumerate(horarios):
        texto_horarios += f"Aulas {i+1}: {horario.get('dia','Dia não especificado')} das {horario.get('horaInicio','HH:MM')} às {horario.get('horaFim','HH:MM')}\n"
    return texto_horarios

def get_strategy_template_content(strategy_key: str, tematica_sa: str) -> str:
    """Retorna o template de conteúdo específico para a estratégia, formatado com a temática."""
    strategy_map = {
        "situacao-problema": modeloPlanoDeEnsinoSP,
        "estudo-de-caso": modeloPlanoDeEnsinoEC,
        "projetos": modeloPlanoDeEnsinoP,
        "pesquisa-aplicada": modeloPlanoDeEnsinoPA,
    }
    template = strategy_map.get(strategy_key.lower().replace(" ", "-"))
    if template:
        return template.format(tematica_sa=tematica_sa if tematica_sa else "Não especificada")
    logger.warning(f"Template de conteúdo não encontrado para estratégia: {strategy_key}")
    return "[ERRO INTERNO: Conteúdo da estratégia não pôde ser gerado devido a template não encontrado]"

def format_estrategia_nome_for_display(strategy_key: str) -> str:
    """Formata o nome da estratégia para exibição no título do Item 4."""
    return strategy_key.replace("-", " ").title()

@tool
async def generate_teaching_plan(
    stored_markdown_id: str, # ID para buscar o Markdown
    docente: str,
    unidade_operacional: str,
    # Os seguintes parâmetros devem vir dos dados extraídos anteriormente ou do input do usuário
    nome_curso: str,
    turma: str,
    nome_uc: str,
    situacoes_aprendizagem_param: List[Dict[str, Any]], # Lista de SAs
    horarios_param: List[Dict[str,str]] = None
) -> str:
    """Gera um plano de ensino detalhado com base no conteúdo Markdown armazenado e parâmetros fornecidos."""
    logger.info(f"Tool: generate_teaching_plan chamada para stored_id: {stored_markdown_id}, UC: {nome_uc}")
    if horarios_param is None:
        horarios_param = []

    markdown_content = await get_markdown_document(stored_markdown_id)
    if not markdown_content:
        err_msg = f"Conteúdo Markdown não encontrado para o ID: {stored_markdown_id}"
        logger.error(err_msg)
        return json.dumps({"error": err_msg, "details": "Markdown content could not be retrieved from storage."})

    final_plan_markdown_parts: List[str] = []
    try:
        llm = await get_plan_generation_llm()
        model = await get_plan_generation_llm()
        
        contexto_inicial_chat = (
            f"Aqui está o conteúdo do Plano de Curso desta Unidade Curricular (UC), que deve servir como base para as informações gerais e "
            f"para a seleção de capacidades e conhecimentos específicos para cada Situação de Aprendizagem (SA):\n\n"
            f"{markdown_content}\n"
            f"Por favor, gere as seções do Plano de Ensino conforme eu for solicitado, "
            f"seguindo os templates e instruções específicas para cada seção. Náo"
        )
        chat_session = model.start_chat(history=[
            {'role': 'user', 'parts': [{'text': contexto_inicial_chat}]}
        ])
        
        # --- ETAPA 1: Gerar Cabeçalho Geral (Item 1) ---
        logger.info("Gerando Item 1: Cabeçalho Geral do Plano de Ensino...")
        # O LLM pode precisar extrair/inferir alguns campos do markdown_content_uc
        # como Carga Horária Total da UC, Objetivo Geral da UC, Módulo.
        # Por simplicidade, vamos assumir que podem ser "a definir" se não passados.
        prompt_cabecalho = (
            f"Com base nas informações fornecidas e no conteúdo do plano de curso em anexo, "
            f"preencha soemente o Item 1 (Informações da Unidade Curricular) do Plano de Ensino. \n"
            f"Informações disponíveis:\n"
            f"- Nome do Curso Técnico: {nome_curso}\n"
            f"- Turma: {turma}\n"
            f"- Nome da Unidade Curricular: {nome_uc}\n"
            f"- Professor Titular: {docente}\n"
            f"- Unidade Operacional (Escola): {unidade_operacional}\n"
            f"Use o seguinte template para o Item 1:\n{modeloCabecalhoPlanoEnsino}"
        )
        # response_item1 = await llm.generate_content_async(prompt_cabecalho)
        response_item1 = await chat_session.send_message_async(prompt_cabecalho)
        final_plan_markdown_parts.append(response_item1.text.strip())
        logger.info("Item 1: Cabeçalho Geral gerado.")

        # --- ETAPA 2: Loop por cada Situação de Aprendizagem ---
        for i, sa_item in enumerate(situacoes_aprendizagem_param):
            sa_num = i + 1
            logger.info(f"Processando SA {sa_num}/{len(situacoes_aprendizagem_param)}...")
            
            sa_capacidades_tecnicas = "\n".join([f"- {cap}" for cap in sa_item.get("capacidades_tecnicas", [])])
            sa_capacidades_socioemocionais = "\n".join([f"- {cap}" for cap in sa_item.get("capacidades_socioemocionais", [])])
            sa_estrategia_key = sa_item.get("estrategia", "situacao-problema") # Default se não vier
            sa_tematica = sa_item.get("tema_desafio", "Não especificado")

            # Gerar Item 2 (Capacidades) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 2 (Capacidades)...")
            prompt_item2 = f"Preencha somente o Item 2 seguindo o template {modeloItem2CapacidadesSA}" + f"Utilize as seguintes capacidades técnicas/básicas: {sa_capacidades_tecnicas}.\n" + f"Utilize as seguintes capacidades socioemocionais: {sa_capacidades_socioemocionais}.\n" + f"Inicie com: \n\n# Situação de Aprendizagem {sa_num}"	
            # Não precisa de LLM aqui se o template for apenas para formatação dos dados já recebidos.
            # Se o LLM for popular algo mais, então a chamada seria necessária.
            # Por simplicidade, vamos preencher diretamente.
            # Adaptação: O LLM pode reescrever ou validar, então uma chamada leve pode ser útil.
            # prompt_item2_llm = f"Formate as seguintes capacidades no padrão do Item 2 do plano de ensino, usando o template abaixo. Capacidades Técnicas a incluir: {sa_capacidades_tecnicas}. Capacidades Socioemocionais a incluir: {sa_capacidades_socioemocionais}.\n\nTEMPLATE:\n{modeloItem2CapacidadesSA}"
            # response_item2 = await llm.generate_content_async(response_item1+prompt_item2) # Chamada para garantir formatação e consistência
            response_item2 = await chat_session.send_message_async(prompt_item2)
            item2_content = response_item2.text.strip()
            final_plan_markdown_parts.append(item2_content)
            logger.info(f"SA {sa_num}: Item 2 (Capacidades) gerado.")
            
            # Gerar Item 3 (Conhecimentos) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 3 (Conhecimentos)...")
            prompt_item3 = f"Preencha somente o Item 3 seguinte o template {modeloItem3ConhecimentosSA} considerando os conhecimentos da unidade curricular {nome_uc} contidas no plano de curso."
            # response_item3 = await llm.generate_content_async(response_item2+prompt_item3)
            response_item3 = await chat_session.send_message_async(prompt_item3)
            item3_content = response_item3.text.strip()
            final_plan_markdown_parts.append(item3_content)
            logger.info(f"SA {sa_num}: Item 3 (Conhecimentos) gerado.")

            # Gerar Item 4 (Estratégia) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 4 (Estratégia)...")
            conteudo_especifico_estrategia = get_strategy_template_content(sa_estrategia_key, sa_tematica)
            if "[ERRO INTERNO:" in conteudo_especifico_estrategia:
                 final_plan_markdown_parts.append(f"\n### 4. Estratégia de Aprendizagem Desafiadora: *{format_estrategia_nome_for_display(sa_estrategia_key)}*\n{conteudo_especifico_estrategia}\n")
                 logger.error(f"SA {sa_num}: Erro ao obter template de conteúdo para estratégia {sa_estrategia_key}")
                 contexto_estrategia_atual = conteudo_especifico_estrategia # Salva o erro para contexto
            else:
                prompt_item4 = modeloItem4EstrategiaSA_Base.format(
                    estrategia_nome_formatado=format_estrategia_nome_for_display(sa_estrategia_key),
                    template_especifico_da_estrategia_aqui=conteudo_especifico_estrategia
                )
                prompt_item4_llm = (
                    f"Preencha somente o item 4 (Estratégia de Aprendizagem Desafiadora) do plano de ensino."
                    f"Leve em consideração a temática da Situação de Aprendizagem: '{sa_tematica}' e as capacidades e conhecimentos elaborados anteriormente."
                    f"Use o seguinte template:\n{prompt_item4}\n"
                )
                # response_item4 = await llm.generate_content_async(item3_content+prompt_item4_llm)
                response_item4 = await chat_session.send_message_async(prompt_item4_llm)
                item4_content = response_item4.text.strip()
                final_plan_markdown_parts.append(item4_content)
                contexto_estrategia_atual = item4_content # Para usar nos próximos itens
                logger.info(f"SA {sa_num}: Item 4 (Estratégia) gerado.")

            # Gerar Item 5 (Avaliação) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 5 (Avaliação)...")
            prompt_item5 = (
                # f"Com base na Situação de Aprendizagem elaborada anteriormente, descrita abaixo:\n"
                # f"\n{contexto_estrategia_atual}\n\n"
                # f"Considere os conhecimentos definidos para esta SA:\n"
                # f"{item3_content}\n\n"
                # f"Considere as capacidades definidas para esta SA: "
                # f"Técnicas: {sa_capacidades_tecnicas}; Socioemocionais: {sa_capacidades_socioemocionais}.\n"
                f"Preencha somente o Item 5 (Critérios de Avaliação para esta Situação de Aprendizagem) usando o template:\n{modeloAvaliacaoAtual}"
            )
            # response_item5 = await llm.generate_content_async(prompt_item5)
            response_item5 = await chat_session.send_message_async(prompt_item5)
            item5_content = response_item5.text.strip()
            final_plan_markdown_parts.append(item5_content)
            contexto_avaliacao_atual = item5_content
            logger.info(f"SA {sa_num}: Item 5 (Avaliação) gerado.")

            # (f) Gerar Item 6 (Plano de Aula) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 6 (Plano de Aula)...")
            # Formatar horários para o prompt de forma legível
            horarios_texto = "\n".join([f"- {h['dia']} das {h['horaInicio']} às {h['horaFim']}" for h in horarios_param]) if horarios_param else "Não fornecidos."
            
            prompt_item6 = (
                # f"Para a Situação de Aprendizagem elaborada anteriormente e descrita abaixo:\n"
                # f"{contexto_estrategia_atual}\n\n"
                # f"Considere os conhecimentos definidos para esta SA:\n"
                # f"{item3_content}\n\n"
                # f"Considere as capacidades definidas para esta SA: "
                # f"Técnicas: {sa_capacidades_tecnicas}; Socioemocionais: {sa_capacidades_socioemocionais}.\n"
                # f"Considere os Critérios de Avaliação:\n"
                # f"{contexto_avaliacao_atual}\n"
                f"Considerando os horários gerais disponíveis para a UC: {horarios_texto}\n"
                f"Preencha somente o Item 6 (Plano de Aula)usando o template:\n{modeloPlanoAulaAtual}"
            )
            # response_item6 = await llm.generate_content_async(prompt_item6)
            response_item6= await chat_session.send_message_async(prompt_item6)
            item6_content = response_item6.text.strip()
            final_plan_markdown_parts.append(item6_content)
            logger.info(f"SA {sa_num}: Item 6 (Plano de Aula) gerado.")

        # --- ETAPA 3: Concatenar e Retornar ---
        final_plan_markdown = "\n".join(final_plan_markdown_parts)
        logger.info(f"Plano de ensino completo com múltiplas SAs gerado com sucesso para UC: {nome_uc}")
        return json.dumps({"plan_markdown": final_plan_markdown}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Erro em generate_teaching_plan: {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao gerar plano de ensino: {str(e)}"}, ensure_ascii=False)
