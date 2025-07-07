import logging
import json
import os
from typing import Optional, List, Any, Dict # Adicionado Dict, Any
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
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
creative_llm = ChatGoogleGenerativeAI(
    model=os.getenv('MODEL_ID'),
    temperature=0.7,
    top_p=0.95,
    max_output_tokens=8192,
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
        llm = creative_llm
        
        instrucao_sistema = (
            "Você é um especialista em educação do Senai que elabora Planos de Ensino detalhados e bem estruturados, "
            "seguindo a Metodologia SENAI de Educação Profissional (MSEP). "
            "Tome como base o conteúdo do plano de curso anexado. "
            "As instruções entre colchetes são orientações específicas para você seguir e não devem aparecer no documento final."
        )
        
        contexto_inicial_chat = (
            f"Aqui está o conteúdo do Plano de Curso desta Unidade Curricular (UC), que deve servir como base para as informações gerais e "
            f"para a seleção de capacidades e conhecimentos específicos para cada Situação de Aprendizagem (SA):\n\n"
            f"{markdown_content}\n"
            f"Por favor, gere as seções do Plano de Ensino conforme eu for solicitado, "
            f"seguindo os templates e instruções específicas para cada seção. Náo"
        )
        
        chat_history = [
            SystemMessage(content=instrucao_sistema),
            HumanMessage(content=contexto_inicial_chat)
        ]
        

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
        
        response_item1 = await llm.ainvoke(chat_history + [HumanMessage(content=prompt_cabecalho)])
        
        
        # Salve o resultado
        item1_content = response_item1.content.strip()
        final_plan_markdown_parts.append(item1_content)
        logger.info("Item 1: Cabeçalho Geral gerado.")
        
        chat_history.append(HumanMessage(content=prompt_cabecalho))
        chat_history.append(AIMessage(content=item1_content))

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
            
            response_item2 = await llm.ainvoke(chat_history + [HumanMessage(content=prompt_item2)])
            
            item2_content = response_item2.content.strip()
            final_plan_markdown_parts.append(item2_content)
            
            chat_history.append(HumanMessage(content=prompt_item2))
            chat_history.append(AIMessage(content=item2_content))
            logger.info(f"SA {sa_num}: Item 2 (Capacidades) gerado.")
            
            # Gerar Item 3 (Conhecimentos) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 3 (Conhecimentos)...")
            prompt_item3 = f"Preencha somente o Item 3 seguinte o template {modeloItem3ConhecimentosSA} considerando os conhecimentos da unidade curricular {nome_uc} contidas no plano de curso."

            response_item3 = await llm.ainvoke(chat_history + [HumanMessage(content=prompt_item3)])
            item3_content = response_item3.content.strip()
            final_plan_markdown_parts.append(item3_content)
            
            chat_history.append(HumanMessage(content=prompt_item3))
            chat_history.append(AIMessage(content=item3_content))
            
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
                prompt_item4 = (
                    f"Preencha somente o item 4 (Estratégia de Aprendizagem Desafiadora) do plano de ensino."
                    f"Leve em consideração a temática da Situação de Aprendizagem: '{sa_tematica}' e as capacidades e conhecimentos elaborados anteriormente."
                    f"Use o seguinte template:\n{prompt_item4}\n"
                )
                
                response_item4 = await llm.ainvoke(chat_history + [HumanMessage(content=prompt_item4)])
                item4_content = response_item4.content.strip()
                final_plan_markdown_parts.append(item4_content)
                chat_history.append(HumanMessage(content=prompt_item4))
                chat_history.append(AIMessage(content=item4_content))
                
                logger.info(f"SA {sa_num}: Item 4 (Estratégia) gerado.")

            # Gerar Item 5 (Avaliação) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 5 (Avaliação)...")
            prompt_item5 = (f"Preencha somente o Item 5 (Critérios de Avaliação para esta Situação de Aprendizagem) usando o template:\n{modeloAvaliacaoAtual}")

            
            response_item5 = await llm.ainvoke(chat_history + [HumanMessage(content=prompt_item5)])
            item5_content = response_item5.content.strip()
            final_plan_markdown_parts.append(item5_content)
            chat_history.append(HumanMessage(content=prompt_item5))
            chat_history.append(AIMessage(content=item5_content))
            
            logger.info(f"SA {sa_num}: Item 5 (Avaliação) gerado.")

            # (f) Gerar Item 6 (Plano de Aula) para esta SA
            logger.info(f"SA {sa_num}: Gerando Item 6 (Plano de Aula)...")
            # Formatar horários para o prompt de forma legível
            horarios_texto = "\n".join([f"- {h['dia']} das {h['horaInicio']} às {h['horaFim']}" for h in horarios_param]) if horarios_param else "Não fornecidos."
            
            prompt_item6 = (
                f"Considerando os horários gerais disponíveis para a UC: {horarios_texto}\n"
                f"Preencha somente o Item 6 (Plano de Aula)usando o template:\n{modeloPlanoAulaAtual}"
            )

            response_item6= await llm.ainvoke(chat_history + [HumanMessage(content=prompt_item6)])
            item6_content = response_item6.content.strip()
            final_plan_markdown_parts.append(item6_content)
            
            chat_history.append(HumanMessage(content=prompt_item6))
            chat_history.append(AIMessage(content=item6_content))
            logger.info(f"SA {sa_num}: Item 6 (Plano de Aula) gerado.")

        # --- ETAPA 3: Concatenar e Retornar ---
        final_plan_markdown = "\n".join(final_plan_markdown_parts)
        logger.info(f"Plano de ensino completo com múltiplas SAs gerado com sucesso para UC: {nome_uc}")
        return json.dumps({"plan_markdown": final_plan_markdown}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Erro em generate_teaching_plan: {e}", exc_info=True)
        return json.dumps({"error": f"Falha ao gerar plano de ensino: {str(e)}"}, ensure_ascii=False)
