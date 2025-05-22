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
async def get_plan_generation_llm(model_name: str = "gemini-1.5-pro-latest", temperature: float = 0.3): # Modelo Pro para tarefa mais complexa
    # ... (Lógica para configurar genai.GenerativeModel como antes)
    # ... (Verifique a configuração da API Key ou ADC para Vertex)
    generation_config_dict = {
        "temperature": temperature, "top_p": 0.95, "max_output_tokens": 8192, # Max tokens para PRO
        "response_mime_type": "text/plain",
    }
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config_dict,
        system_instruction="Você é um especialista em elaborar Planos de Ensino detalhados e bem estruturados, seguindo a Metodologia SENAI de Educação Profissional (MSEP).",
    )

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
    tematica: Optional[str] = None
    # extracted_initial_data: Optional[Dict[str, Any]] = None # Alternativa: passar um dict com os dados extraídos
) -> str:
    """
    Gera um plano de ensino completo.
    stored_markdown_id: O ID do documento Markdown armazenado (em GCS via DB).
    docente: Nome do docente.
    unidade_operacional: Nome da escola/unidade.
    nome_curso: Nome do curso (obtido da extração inicial).
    nome_uc: Nome da Unidade Curricular (obtido da extração inicial).
    capacidades_tecnicas: Lista de capacidades técnicas (obtidas da extração inicial).
    capacidades_socioemocionais: Lista de capacidades socioemocionais (obtidas da extração inicial).
    estrategia: A estratégia de ensino a ser utilizada.
    tematica: O tema gerador (opcional, dependendo da estratégia).
    Retorna uma string JSON com o 'plan_markdown'.
    """
    logger.info(f"Tool: generate_teaching_plan chamada para stored_markdown_id: {stored_markdown_id}")

    markdown_content = await get_markdown_document(stored_markdown_id)
    if not markdown_content:
        err_msg = f"Conteúdo Markdown não encontrado para o ID: {stored_markdown_id}"
        logger.error(err_msg)
        return json.dumps({"error": err_msg, "details": "Markdown content could not be retrieved from storage."})

    try:
        llm = await get_plan_generation_llm()

        # Prepara o objeto de parâmetros para a função de formatação de prompt
        # (Usando MockPlanParams de plan_logic.py para clareza de estrutura)
        plan_params_for_formatter = MockPlanParams() # type: ignore
        plan_params_for_formatter.uc = nome_uc
        plan_params_for_formatter.curso = nome_curso
        plan_params_for_formatter.estrategia = estrategia
        plan_params_for_formatter.unidade = unidade_operacional
        plan_params_for_formatter.docente = docente
        plan_params_for_formatter.capacidadesTecnicas = capacidades_tecnicas
        plan_params_for_formatter.capacidadesSocioemocionais = capacidades_socioemocionais
        plan_params_for_formatter.tematica = tematica
        
        # Etapa 1: Gerar a estrutura inicial e SA/EC/P/PA (Seções 1-4)
        initial_plan_prompt = format_initial_prompt_for_plan(plan_params_for_formatter, markdown_content)
        if "ERRO:" in initial_plan_prompt: # Checa se a formatação do prompt falhou
            logger.error(f"Erro ao formatar prompt inicial do plano: {initial_plan_prompt}")
            return json.dumps({"error": initial_plan_prompt, "details": "Failed to format initial teaching plan prompt."})

        logger.debug(f"Prompt Seção 1-4 (Geração Plano Tool):\n{initial_plan_prompt[:500]}...")
        response_part1 = await llm.generate_content_async(initial_plan_prompt)
        plan_part1_content = response_part1.text

        # Etapa 2: Gerar Critérios de Avaliação (Seção 5)
        prompt_part2_evaluation = f"""Considerando a Situação de Aprendizagem (ou Estudo de Caso, Projeto, Pesquisa Aplicada) e a estrutura do plano de ensino descrita abaixo:
        {plan_part1_content}

        Elabore APENAS e EXCLUSIVAMENTE o item "5. Critérios de Avaliação", seguindo o modelo fornecido.
        Modelo dos Critérios de Avaliação:
        {modeloAvaliacaoAtual}"""
        logger.debug(f"Prompt Seção 5 (Geração Plano Tool):\n{prompt_part2_evaluation[:500]}...")
        response_part2 = await llm.generate_content_async(prompt_part2_evaluation)
        plan_part2_evaluation_criteria = response_part2.text

        # Etapa 3: Gerar Plano de Aula e Perguntas Mediadoras (Seções 6-7)
        context_for_lesson_plan = plan_part1_content + "\n\n" + plan_part2_evaluation_criteria
        prompt_part3_lesson_plan = f"""Com base no plano de ensino desenvolvido até a seção de critérios de avaliação, conforme abaixo:
        {context_for_lesson_plan}

        Elabore APENAS e EXCLUSIVAMENTE os itens "6. Plano de Aula" e "7. Perguntas Mediadoras", seguindo o modelo fornecido.
        Modelo do Plano de Aula e Perguntas:
        {modeloPlanoAulaAtual}"""
        logger.debug(f"Prompt Seção 6-7 (Geração Plano Tool):\n{prompt_part3_lesson_plan[:500]}...")
        response_part3 = await llm.generate_content_async(prompt_part3_lesson_plan)
        plan_part3_lesson_and_questions = response_part3.text

        final_plan_markdown = (
            plan_part1_content.strip() + "\n\n" +
            plan_part2_evaluation_criteria.strip() + "\n\n" +
            plan_part3_lesson_and_questions.strip()
        ).strip()
        
        logger.info(f"Plano de ensino gerado com sucesso para stored_markdown_id: {stored_markdown_id}")
        return json.dumps({"plan_markdown": final_plan_markdown})

    except Exception as e:
        logger.error(f"Erro em generate_teaching_plan: {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao gerar plano de ensino: {str(e)}", "details": str(e)})
