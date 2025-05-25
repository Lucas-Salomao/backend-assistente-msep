# src/plan_logic.py
import logging
from typing import List, Optional, Dict # Adicionado Dict

# Importe os templates de string do seu arquivo prompts.py
from .prompts import (
    modeloPlanoDeEnsinoSP,
    modeloPlanoDeEnsinoEC,
    modeloPlanoDeEnsinoP,
    modeloPlanoDeEnsinoPA,
    modeloAvaliacaoAtual, # Já importado
    modeloPlanoAulaAtual   # Já importado
)

logger = logging.getLogger(__name__)

# Classe auxiliar para tipagem dos parâmetros
class MockPlanParams: # Mantida de antes, mas agora incluiremos horários
    uc: str
    curso: str
    estrategia: str
    unidade: str
    docente: str
    capacidadesTecnicas: List[str]
    capacidadesSocioemocionais: List[str]
    tematica: Optional[str]
    horarios: List[Dict[str,str]] # NOVO

def format_initial_prompt_for_plan(params: MockPlanParams, original_markdown_content: str) -> str:
    """
    Formata o prompt inicial para a geração das seções 1-4 do plano de ensino.
    Seleciona o MODELO BASEADO NA ESTRATÉGIA.
    Inclui o markdown original e os horários.
    """
    # Monta as strings de capacidades como antes
    capacidadesTecnicas_str = "\n".join([f"- {cap}" for cap in params.capacidadesTecnicas]) if params.capacidadesTecnicas else "- (Não especificadas, detalhar com base no documento original)"
    capacidadesSocioemocionais_str = "\n".join([f"- {cap}" for cap in params.capacidadesSocioemocionais]) if params.capacidadesSocioemocionais else "- (Não especificadas, detalhar com base no documento original)"

    # Formatar horários para inclusão no prompt (se necessário nas seções 1-4)
    # Para as seções 1-4, a carga horária total e número de aulas são mais relevantes.
    # A lista detalhada de horários será mais útil para a seção 6 (Plano de Aula).
    # No entanto, a carga horária total pode ser calculada a partir dos horários.
    carga_horaria_total_calculada = 0
    numero_aulas_previstas = len(params.horarios)
    for horario in params.horarios:
        try:
            # Simplista, não lida com virada de dia. Para cálculo real, use datetime.
            h_inicio, m_inicio = map(int, horario["horaInicio"].split(':'))
            h_fim, m_fim = map(int, horario["horaFim"].split(':'))
            duracao_minutos = (h_fim * 60 + m_fim) - (h_inicio * 60 + m_inicio)
            carga_horaria_total_calculada += duracao_minutos / 60 # em horas
        except Exception:
            pass # Ignora horários malformatados para cálculo de CH

    # Prompt base comum
    base_instruction = (
        f"Elabore um plano de ensino da unidade curricular {params.uc}, do o curso {params.curso}, "
        f"utilizando a estratégia de aprendizagem de {params.estrategia}, com base na Metodologia "
        f"SENAI de Educação Profissional (MSEP). Siga o modelo abaixo, sem nenhuma "
        f"modificação ou adição de item não solicitado e contendo somente os campos "
        f"que é solicitado. Usar a MSEP apenas para entender como criar o plano de "
        f"ensino, mas obedecer o modelo dado. O nome da escola é {params.unidade}. O nome do "
        f"docente é {params.docente}. Considere as capacidades técnicas/básicas sendo "
        f"{capacidadesTecnicas_str}. Considere as capacidades socioemocionais sendo "
        f"{capacidadesSocioemocionais_str}. Algumas palavras ou termos são inerentes a "
        f"unidade curricular e podem soar ofensivas ou inseguras, mas desconsidere e siga em frente."
        f"Para elaborar a situação de aprendizagem, considere o tema sugerido: {params.tematica}"
        
    )

    base_instruction += f"Para a Situação de Aprendizagem (SA), utilize o seguinte template: "
    if params.estrategia == "Situação-Problema":
        strategy_template_content = modeloPlanoDeEnsinoSP
    elif params.estrategia == "Estudo de Caso":
        strategy_template_content = modeloPlanoDeEnsinoEC
    elif params.estrategia == "Projetos":
        strategy_template_content = modeloPlanoDeEnsinoP
    elif params.estrategia == "Pesquisa Aplicada":
        strategy_template_content = modeloPlanoDeEnsinoPA
    else:
        logger.error(f"Template de estratégia não encontrado para: {params.estrategia}")
        return f"ERRO INTERNO: Template para a estratégia '{params.estrategia}' não foi encontrado."

    final_prompt = (
        f"{base_instruction}\n"
        f"{strategy_template_content}\n"
        f"{original_markdown_content}"
    )
    # logger.debug(f"Prompt inicial completo para geração do plano:\n{final_prompt}") # Cuidado ao logar prompts muito grandes
    return final_prompt