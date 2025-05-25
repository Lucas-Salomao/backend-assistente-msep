import logging
import json
import os
from typing import Optional, List, Any, Dict # Adicionado Dict, Any
from langchain_core.tools import tool
import google.generativeai as genai # Ou sua forma preferida de acessar o LLM

from src.document_store import get_markdown_document # Para buscar o Markdown
from src.plan_logic import ( # Lógica e templates de prompt
    format_initial_prompt_for_plan,
    modeloAvaliacaoAtual,
    modeloPlanoAulaAtual,
    MockPlanParams # Se a classe helper for usada
)

logger = logging.getLogger(__name__)

# Função auxiliar para o LLM (pode ser movida para um utils)
async def get_plan_generation_llm(model_name: str = os.getenv('MODEL_ID'), temperature: float = 0.7): # Modelo Pro para tarefa mais complexa
    generation_config_dict = {
        "temperature": temperature, "top_p": 0.95, "max_output_tokens": 8192, # Max tokens para PRO
        "response_mime_type": "text/plain",
    }
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config_dict,
        system_instruction="Você é um especialista em elaborar Planos de Ensino detalhados e bem estruturados, seguindo a Metodologia SENAI de Educação Profissional (MSEP).",
    )
    
def format_horarios_for_plano_aula(horarios: List[Dict[str,str]]) -> str:
    """Formata a lista de horarios para inclusão no prompt do plano de aula."""
    if not horarios:
        return "Nenhum horário de aula específico foi fornecido. O plano de aula deve ser genérico em relação a datas e horários."
    
    texto_horarios = "Os encontros previstos são:\n"
    for i, horario in enumerate(horarios):
        texto_horarios += f"Aulas {i+1}: {horario.get('dia','Dia não especificado')} das {horario.get('horaInicio','HH:MM')} às {horario.get('horaFim','HH:MM')}\n"
    return texto_horarios

@tool
async def generate_teaching_plan(
    stored_markdown_id: str, # ID para buscar o Markdown
    docente: str,
    unidade_operacional: str,
    # Os seguintes parâmetros devem vir dos dados extraídos anteriormente ou do input do usuário
    nome_curso: str,
    nome_uc: str,
    capacidades_tecnicas: List[str],
    capacidades_socioemocionais: List[str],
    estrategia: str, # 'Situação-Problema', 'Estudo de Caso', etc.
    tematica: Optional[str] = None,
    horarios_param: List[Dict[str,str]] = None
) -> str:
    """Gera um plano de ensino detalhado com base no conteúdo Markdown armazenado e parâmetros fornecidos."""
    logger.info(f"Tool: generate_teaching_plan chamada para stored_id: {stored_markdown_id}, UC: {nome_uc}, Estratégia: {estrategia}")
    if horarios_param is None:
        horarios_param = []

    markdown_content = await get_markdown_document(stored_markdown_id)
    if not markdown_content:
        err_msg = f"Conteúdo Markdown não encontrado para o ID: {stored_markdown_id}"
        logger.error(err_msg)
        return json.dumps({"error": err_msg, "details": "Markdown content could not be retrieved from storage."})

    try:
        llm = await get_plan_generation_llm()

        plan_params = MockPlanParams() # type: ignore
        plan_params.uc = nome_uc
        plan_params.curso = nome_curso
        plan_params.estrategia = estrategia
        plan_params.unidade = unidade_operacional
        plan_params.docente = docente
        plan_params.capacidadesTecnicas = capacidades_tecnicas
        plan_params.capacidadesSocioemocionais = capacidades_socioemocionais
        plan_params.tematica = tematica
        plan_params.horarios = horarios_param
        
        # Etapa 1: Gerar a estrutura inicial e SA/EC/P/PA (Seções 1-4)
        initial_plan_prompt = format_initial_prompt_for_plan(plan_params, markdown_content)
        if "ERRO INTERNO:" in initial_plan_prompt: # Checa se a formatação do prompt falhou
            logger.error(f"Erro ao formatar prompt inicial do plano: {initial_plan_prompt}")
            return json.dumps({"error": initial_plan_prompt, "details": "Failed to format initial teaching plan prompt."})
        logger.debug(f"Gerando Plano de Ensino: Cabeçalho, Capacidades, Conhecimento e Estratégia de aprendizagem desafiadora...")
        response_part1 = await llm.generate_content_async(initial_plan_prompt)
        plan_part1_content = response_part1.text.strip()
        logger.info("Seções Cabeçalho, Capacidades, Conhecimento e Estratégia de aprendizagem desafiadora geradas.")

        # Etapa 2: Gerar Critérios de Avaliação (Seção 5)
        prompt_part2_evaluation = f"""Elaborar somente o item 5. Critérios de Avaliação de acordo com a situação de aprendizagem proposta.
        {plan_part1_content}
        Elabore APENAS e EXCLUSIVAMENTE o item "5. Critérios de Avaliação", seguindo o modelo fornecido.
        Modelo dos Critérios de Avaliação:
        {modeloAvaliacaoAtual}"""
        logger.debug(f"Gerando Plano de Ensino: Critérios de Avaliação...")
        response_part2 = await llm.generate_content_async(prompt_part2_evaluation)
        plan_part2_evaluation_criteria = response_part2.text.strip()

        # Etapa 3: Gerar Plano de Aula (Seções 6)
        context_for_lesson_plan = plan_part1_content + "\n\n" + plan_part2_evaluation_criteria
        horarios_formatados_para_prompt = format_horarios_for_plano_aula(plan_params.horarios)
        prompt_part3_lesson_plan = f"""Com base no plano de ensino desenvolvido até a seção de critérios de avaliação, conforme abaixo:
        {context_for_lesson_plan}
        E considerando os seguintes horários de aula definidos:\n{horarios_formatados_para_prompt}\n\n"
        Elabore APENAS e EXCLUSIVAMENTE os itens "6. Plano de Aula", seguindo o modelo fornecido.
        Modelo do Plano de Aula e Perguntas:
        {modeloPlanoAulaAtual}"""
        logger.debug(f"Gerando Plano de Ensino: Plano de Aula...")
        response_part3 = await llm.generate_content_async(prompt_part3_lesson_plan)
        plan_part3_lesson_and_questions = response_part3.text.strip()

        final_plan_markdown = (
            plan_part1_content + "\n\n" +
            plan_part2_evaluation_criteria + "\n\n" +
            plan_part3_lesson_and_questions
        ).strip()
        
        logger.info(f"Plano de ensino gerado com sucesso para stored_markdown_id: {stored_markdown_id}")
        return json.dumps({"plan_markdown": final_plan_markdown})

    except Exception as e:
        logger.error(f"Erro em generate_teaching_plan: {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao gerar plano de ensino: {str(e)}", "details": str(e)})
