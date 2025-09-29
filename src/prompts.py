modeloCabecalhoPlanoEnsino="""
# Plano de Ensino segundo a MSEP

## Informações do Curso

**Curso:** [Nome do curso]

**Turma:** [Nome da turma]

**Unidade Curricular (UC):** [Nome da unidade curricular]

**Módulo:** [Básico ou Específico]

**Carga Horária total na UC:** [Carga horária total do curso]

**Objetivo da Unidade Curricular:** [Objetivo geral da unidade curricular de acordo com o plano de curso]

**Modalidade de ensino:** [Presencial, EAD ou Híbrida]

**Professor Titular:** [Nome do professor titular]

**Unidade:** [Escola Senai]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""
modeloItem2CapacidadesSA="""
## Capacidades a serem desenvolvidas:

### Capacidades Básicas [Somente para Módulo Básico]:

[
    -Liste aqui todas as capacidades Básicas que foram passadas para o prompt, escolhidas pelo professor, independente da quantidade.
    -Cada capacidade deve ficar em uma linha separada.
    -Caso não tenha sido passado nenhuma capacidade, escolha no máximo cinco capacidades básicas que são necessárias o desenvolvimento da situação de aprendizagem proposta.
    -Liste somente as capacidades escolhidas e nada mais, respeitado a quantiadade máximo de cinco capacidades, quando escolhidas de forma automática e aleatória.
] 

### Capacidades Técnicas [Somente para Módulo Específico]:

[
    -Liste aqui todas as capacidades Técnicas que foram passadas para o prompt, escolhidas pelo professor, independente da quantidade.
    -Cada capacidade deve ficar em uma linha separada.
    -Caso não tenha sido passado nenhuma capacidade, escolha no máximo cinco técnicas que são necessárias o desenvolvimento da situação de aprendizagem proposta.
    -Liste somente as capacidades escolhidas e nada mais, respeitado a quantiadade máximo de cinco capacidades, quando escolhidas de forma automática e aleatória.
]

### Capacidades Socioemocionais:

[
    -Liste aqui todas as capacidades Socioemocionais que foram passadas para o prompt, escolhidas pelo professor, independente da quantidade.
    -Cada capacidade deve ficar em uma linha separada.
    -Caso não tenha sido passado nenhuma capacidade, escolha no máximo três capacidades socioemocionais que são necessárias para o desenvolvimento da situação de aprendizagem proposta.
    Liste somente as capacidades escolhidas e nada mais, respeitado a quantiadade máximo de três capacidades, quando escolhidas de forma automática e aleatória.
]

[
    - Nesse campo, precisamos selecionar algumas (não todas) capacidades que serão desenvolvidas na Situação de Aprendizagem (sejam básicas, técnicas e socioemocionais).
    - Ao selecionarmos as capacidades que serão desenvolvidas, precisamos cuidar da gradualidade das capacidades, trabalhando com propostas que contemplem capacidades de menor complexidade para maior complexidade.
    - Importante: não podemos alterar as capacidades previstas no plano de curso.
    - Exemplo: do verbo identificar para o verbo configurar, temos uma diferença grande na complexidade da capacidade preterida.
    - Escolher somente as capacidades que são necessárias para o desenvolvimento da situação de aprendizagem, de acordo com a unidade curricular do plano de curso, se atentando para não escolher todas as capacidades da unidade curricular.
]

Incluir ao final deste bloco: ⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente\n\n
"""
modeloItem3ConhecimentosSA="""
## Conhecimentos:

[
    - Lista numerada com hierarquia de tópicos e sub-tópicos.
    - Listar os conhecimentos, precedidos da numeração assim como aparecem no plano de curso.
    - Cada conhecimento deve ficar em uma linha separada.
    - É muito importante que a lista não tenha todos os conhecimentos da unidade curricular, pois outras situações de aprendizagem podem ser criadas com os conhecimentos não selecionados.
    - Escolher somente os conhecimentos que são necessários para o desenvolvimento da situação de aprendizagem, de acordo com as capacidades escolhidas no item Capacidades a serem desenvolvidas, se atentando para não escolher todos os conhecimentos da unidade curricular em questão.

    Exemplo:
    1. Conhecimento 1
        1.1 Subtópico 1
        1.2 Subtópico 2
    2. Conhecimento 2
        2.1 Subtópico 1
        2.2 Subtópico 2
    3. Conhecimento 3
        3.1 Subtópico 1
        3.2 Subtópico 2
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""

modeloItem4EstrategiaSA_Base="""
## Estratégia de aprendizagem desafiadora: *{estrategia_nome_formatado}*

[
    Indicar o tipo de estratégia de aprendizagem escolhida em itálico
]

**Nº de aulas previstas para desenvolver esta Situação de Aprendizagem:** [Estimar com base na complexidade, carga horária da UC e horários disponíveis. Ex: 10 aulas]\n
**Carga horária prevista para o desenvolvimento desta Situação de Aprendizagem:** [Estimar em horas. Ex: 30 horas]\n

### Título da Situação de Aprendizagem:
[
    - Inserir título da Situação de Aprendizagem, relacionado à unidade curricular selecionada.
    - O título deve ser claro, objetivo e refletir o tema da situação de aprendizagem.
]	

{template_especifico_da_estrategia_aqui}
Incluir ao final deste bloco: ⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""
modeloPlanoDeEnsinoSP="""
[
    Propor uma Situação de Aprendizagem de acordo com as capacidades escolhidas no item Capacidades a serem desenvolvidas e com os conhecimentos escolhidos no item anterior.
    Esse texto não deve conter no plano é apenas a referência de como elaborar a situação de aprendizagem.
]

### Contextualização:

[ 
    - Descrição da contextualização da Situação de Aprendizagem.
    - Nesse campo, a abordagem contextualizada é pensada para construir cenários reais da situação de trabalho que o aluno vai enfrentar. Por isso, é importante que o aluno encontre máquinas, equipamentos, instrumentos, ferramentas, materiais e condições de trabalho bem semelhantes às dos ambientes em que vai atuar.
    - Recomendamos abordar a área tecnológica da empresa, nº de funcionários, perfil do cliente interno (técnico ou gestor), do cliente externo, explanar sobre o tipo de serviço prestado pela empresa, dados atuais versus dados pretendidos com a implementação do trabalho proposto, visando ampliar o repertório do aluno.
    - Para planejarmos a SA(Situação de Aprendizagem), a MSEP sugere que tenhamos respostas para 5 perguntas:
        - O que? Para que? Como? Com o que? Onde?
    - Com as respostas às essas perguntas, precisamos considerar 3 requisitos para o planejamento:
        - Mobilização.
        - Resolução de problemas com tomada de decisão.
        - Máximo de circulação de informações possíveis.
    - Estimulamos as competências de visão sistêmica e de criatividade com a Situação de Aprendizagem?
    - Sugerir a necessidade de inclusão de figuras, esquemas, desenhos, leiaute, formulários, etc, para complementar a sitação de aprendizagem e descrever que imagem deve ser incluída, se for o caso.
]

### Desafio:

[
    - Descrição do desafio proposto na Situação de Aprendizagem.
    - A MSEP recomenda que o desafio da SA precisa ser diferente do que o aluno já realizou, mas isso não significa que precisa ser inédito.
    - Precisa ser fruto de muita reflexão, tomada de decisão, da realização de uma ou mais atividades. Precisamos ficar atentos ao que chamamos de “resposta pronta”.
    - Quando as capacidades e conhecimentos requerem análise de dados, comparação ou correlação de soluções alternativas, como a escola propôs, é interessante abordar na perspectiva do estudo de caso e os alunos precisam trazer soluções de sucesso ou insucesso.
]

### Resultados Esperados:

[
    - Descrição detalhada dos resultados esperados dos alunos.
    - A MSEP nos orienta que, ao redigir a estratégia de aprendizagem desafiadora, o docente deve informar claramente o que espera do aluno como um produto final: relatório, trabalho escrito, projeto, protótipo, produto (bem ou serviço), maquete, softwares, vídeos, manuais, pareceres, leiaute, entre outros. Esses resultados devem ser adequados e proporcionais à contextualização e ao nível de exigência do desafio proposto. (p.138 MSEP)
]

NÃO INCLUIR ESSA SESSÃO NO PLANO DE ENSINO, APENAS PARA USO DO PROMPT
[
    Observações:
    - Utilize a linguagem clara e objetiva.
    - Inclua exemplos e informações relevantes para cada item.
    - Mantenha a coerência entre as diferentes etapas do plano de ensino.
    - Use a MSEP para entender como elaborar cada item solicitado.
    - A contextualização da estratégia de aprendizagem deve ser de acordo com o perfil profissional e trazer situações reais do mundo do trabalho.
    - Esta obeservação é apenas para o prompt, não deve conter no plano de ensino.
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""

modeloPlanoDeEnsinoEC="""
### Título do Estudo de Caso:
[
    Insira um título que seja interessante e que reflita o tema do caso
]

### Área Tecnológica:
[
    Área Tecnologica, segundo o Plano de Curso
]

### Segmento:
[
    Segmento segundo o Plano de Curso
]

### Ocupação:
[
    Ocupação segundo o Plano de Curso
]

### Cenário:
[
    Descreva a situação real ou fictícia em que o caso se insere, com detalhes sobre a empresa, o setor, o contexto e a problemática
]

### Desafio:

#### Problema:
[
    Apresente o problema central do estudo de caso, de forma clara e objetiva. Este problema deve ser um desafio relevante para o aluno, ligado à ocupação e ao cenário
]
#### Objetivo:
[
    Defina o que os alunos devem realizar para solucionar o problema. O objetivo deve ser específico e mensurável
]

### Soluções:

#### Solução 1:
[
    Apresente uma solução para o problema, com suas vantagens, desvantagens e implicações.
]
#### Solução 2:
[
    Apresente outra solução, com suas vantagens, desvantagens e implicações.
]
#### Solução 3:
[
    Apresente uma terceira solução (opcional), com suas vantagens, desvantagens e implicações.
]

### Questões para Debate:
[
    - Formule perguntas que incentivem os alunos a analisar criticamente as soluções e a justificar suas escolhas, utilizando os conhecimentos adquiridos.
    - Incorpore questões que promovam o debate sobre as implicações sociais, éticas e ambientais das soluções.
]

NÃO INCLUIR ESSA SESSÃO NO PLANO DE ENSINO, APENAS PARA USO DO PROMPT
[
    Dicas:
    - Utilize uma linguagem clara e concisa.
    - Apresente a situação de forma envolvente e desafiadora.
    - Mantenha a relevância e a conexão com a realidade profissional.
    - Incentive a criatividade e o pensamento crítico.
    - Inclua questões para estimular o debate.
    - Esta obeservação é apenas para o prompt, não deve conter no plano de ensino.
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""

modeloPlanoDeEnsinoP="""
### Título do Projeto:
[
    Insira o título do projeto, relacionado ao tema da unidade curricular
]

### Objetivo do Projeto:
[
    Descreva o objetivo geral do projeto, alinhado com as capacidades a serem desenvolvidas na unidade curricular.
]

### Público Alvo:
[
    Indique o público-alvo do projeto, considerando o nível de ensino, a experiência profissional dos alunos e as necessidades específicas da turma.
]

### Contexto:
[
    Apresente um cenário real ou fictício, contextualizado com a área de atuação profissional e os desafios que o projeto visa solucionar. A contextualização deve ser relevante para os alunos e despertar o interesse.
]

### Desafio:
[
    Defina o problema ou desafio que o projeto pretende resolver. O desafio deve ser específico, complexo e instigante para os alunos, desafiando-os a mobilizar conhecimentos e habilidades.
]

### Resultados Esperados:
[
    Descreva os resultados tangíveis que se espera alcançar com o projeto. Os resultados devem ser mensuráveis e devem estar diretamente relacionados com as capacidades a serem desenvolvidas.
]

### Etapas do Projeto:
[
    Divida o projeto em etapas com prazos e entregas definidas. Detalhe as atividades a serem realizadas em cada etapa e os recursos necessários.
]

### Possibilidade de aplicação no mundo do trabalho:
[
    Descreva como o projeto pode ser aplicado em situações reais do mundo do trabalho, mostrando a relevância prática da aprendizagem.
]

NÃO INCLUIR ESSA SESSÃO NO PLANO DE ENSINO, APENAS PARA USO DO PROMPT
[
    Observações:
    - O projeto deve ser flexível e permitir adaptações durante o processo de desenvolvimento.
    - O Docente deve atuar como mediador do projeto, orientando e apoiando os alunos em cada etapa.
    - O projeto deve incentivar a autonomia, a criatividade e a colaboração entre os alunos.
    - Esta obeservação é apenas para o prompt, não deve conter no plano de ensino.
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""

modeloPlanoDeEnsinoPA="""
### Título:
[
    Inserir título da pesquisa aplicada, relacionado à unidade curricular selecionada
]

### Problema:
[
    Descrever o problema a ser investigado, com base em uma situação real ou hipotética da área da unidade curricular selecionada.
]

### Objetivo:
[
    Definir o objetivo geral da pesquisa aplicada, explicitando o que se pretende alcançar com a investigação.
]

### Justificativa:
[
    Explicar a importância da pesquisa aplicada, destacando a relevância para a área da unidade curricular selecionada, os impactos esperados e a contribuição para a prática profissional.
]

### Metodologia:
[
    - Abordagem:
        [
            Descrever a abordagem metodológica a ser utilizada, como quantitativa, qualitativa ou mista.
        ]
    - Delineamento da pesquisa aplicada:
        [
            Especificar o tipo de delineamento, como estudo de caso, pesquisa exploratória, pesquisa experimental, entre outros.
        ]
    - População e amostra:
        [
            Definir a população e a amostra do estudo, justificando a escolha.
        ]
    - Instrumentos de coleta de dados:
        [
            Indicar os instrumentos de coleta de dados a serem utilizados, como questionários, entrevistas, observação, análise documental, entre outros.
        ]
    - Técnicas de análise de dados:
        [
            Descrever as técnicas de análise de dados a serem empregadas, como análise estatística, análise de conteúdo, análise de discurso, entre outros.
        ]
]

### Etapas da pesquisa aplicada:
[
    Descrever as etapas da pesquisa, com detalhamento das atividades a serem realizadas em cada etapa.
]

### Cronograma:
[
    Criar um cronograma detalhado com as datas previstas para cada etapa da pesquisa.
]

### Recursos:
[
    Listar os recursos necessários para a realização da pesquisa, como materiais, equipamentos, softwares, acesso a dados, etc.
]

### Referências bibliográficas:
[
    Listar as principais referências bibliográficas que serão utilizadas na pesquisa.
]

NÃO INCLUIR ESSA SESSÃO NO PLANO DE ENSINO, APENAS PARA USO DO PROMPT
[
    Observações:
    - Utilize a linguagem clara e objetiva.
    - Inclua exemplos e informações relevantes para cada item.
    - Mantenha a coerência entre as diferentes etapas do plano de ensino.
    - Use a MSEP para entender como elaborar cada item solicitado.
    - A contextualização da estratégia de aprendizagem deve ser de acordo com o perfil profissional e trazer situações reais do mundo do trabalho.
    - Esta obeservação é apenas para o prompt, não deve conter no plano de ensino.
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""

modeloAvaliacaoAtual="""

## Critérios de Avaliação:
[
### Critérios Dicotômicos
    
    Tabela contendo como título "### Instrumento de Registro" 
        Nome do aluno:______________________________________________    Turma:_______________________\n
    - Colunas:
        Capacidades básicas/técnicas e socioemocionais
            [
                Colocar uma capacidades basicas ou técnicas e socioemocionais selecionadas para a situação de aprendizagem por linha.
            ]
        Critérios de Avaliação:
            [
                Para cada capacidade, elaborar dois critérios de avaliação pelo método Dicotômico.
                A MSEP enfatiza a importância de critérios objetivos que:
                    - Sejam específicos para cada tarefa, produto ou comportamento a ser avaliado: Os critérios devem ser elaborados de forma precisa, indicando exatamente o que se espera do aluno.
                    - Descrevam níveis de desempenho esperados: Os critérios devem detalhar diferentes níveis de proficiência, permitindo que o docente avalie o progresso do aluno em relação aos objetivos de aprendizagem.
                    - Representem, no conjunto, um resultado que permita concluir se a capacidade foi desenvolvida: A combinação dos critérios deve fornecer uma visão completa sobre o desenvolvimento da capacidade do aluno.
                    - Deve ser objetivo e possível mensurar ou quantificar, para que se torne um critério concreto, livre de subjetividade.
            ]
        Autoavaliação: [célula em branco]
        Avaliação Professor: [célula em branco]
    - Legenda:
        S=Atingiu/N=Não Atingiu [não preencher na tabela]
    
    Não utilizar a marcação <br> para quebra de linha
    Obedecer a seguinte formatação da tabela em markdown e adequar seguindo o modelo para a quantidade de capacidades:
    
| Capacidades  | Critérios de Avaliação| Autoavaliação | Avaliação |
| -------------| --------------------- | ------------- | --------- |
| [capacidade] | [Critério Dicotômico] |               |           |
|              | [Critério Dicotômico] |               |           |
| [capacidade] | [Critério Dicotômico] |               |           |
|              | [Critério Dicotômico] |               |           |
| [capacidade] | [Critério Dicotômico] |               |           |
|              | [Critério Dicotômico] |               |           |

### Critérios Graduais

    Tabela contendo como título "### Instrumento de Registro"
        Nome do aluno:______________________________________________Turma:_______________________\n
    - Colunas:
        Capacidades básicas/técnicas e socioemocionais
            [
                Colocar uma capacidades basicas ou técnicas e socioemocionais selecionadas para a situação de aprendizagem por linha. Devem ser as mesmas selecionadas no item Critérios Dicotômicos.
            ]
        Nível 1: Descreve o desempenho mínimo esperado do aluno, com características de falta de conhecimento ou domínio.
        Nível 2: Descreve o desempenho do aluno que demonstra alguma compreensão da capacidade, mas ainda precisa de auxílio.
        Nível 3: Descreve o desempenho do aluno que demonstra domínio da capacidade, realizando a tarefa com autonomia e segurança.
        Nível 4: Descreve o desempenho do aluno que demonstra excelência na capacidade, com iniciativa, criatividade e domínio aprofundado.
        
    Obedecer a seguinte formatação da tabela em markdown e adequar seguindo o modelo para a quantidade de capacidades:
        
| **Capacidades**   | **Nível 1**    | **Nível 2**    | **Nível 3**    | **Nível 4**    |
|:-----------------:|:--------------:|:--------------:|:--------------:|:--------------:|
| [capacidade]      |critério nível 1|critério nível 2|critério nível 3|critério nível 4|
| [capacidade]      |critério nível 1|critério nível 2|critério nível 3|critério nível 4|

]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""
modeloPlanoAula="""

## Plano de Aula:
[
    Tabela contendo como título "Plano de Aula"
    - Colulas:
        -Nº horas/aula e data:
            [carga horária em horas e data da aula no formato (DD/MM/AAAA)]
        -Capacidades a serem desenvolvidas:
            [ Listar as capacidades selecionadas anteriormente para a situação de aprendizagem.]
        -Conhecimentos relacionados:
            [ Listar os conhecimentos selecionados anteriormente para o desenvolvimento da situação de aprendizagem.]
        -Estratégias de ensino e instrumentos de avaliação:
            [ Por exemplo:
                - Exposição dialogada: explorar sobre os principais conhecimentos associados ao mercado no que tange às normas e legislações.
                - Simulação: elaboração e aplicação de ficha de análise de investigação de acidentes.
                - Dinâmica de grupo: conversando com as famílias das vítimas de acidente de trabalho.
            ]
        -Recursos e ambientes pedagógicos:
            [Computador, internet, notion, Microsoft Teams, Microsoft Learn, Plataforma de Gamificação Quizziz, Forms, Mentimeter, Kahoot, entre outros.]
        -Critérios de Avaliação:
            [ Listar os critérios de avaliação, críticos e desejáveis, elaborados anteriormente necessários para a avaliação da situação de aprendizagem proposta.]
        -Instrumento de Avaliação:
            [ Definir instrumentos de avaliação de forma a evidenciar os critérios de avaliação, em função das estratégias de ensino.]
        -Referências bibliográficas de acordo com o plano de curso:
            [livros, apostilas, sites, blogs, artigos, etc]
    
    O Plano de Aula deve contemplar toda a carga horária e número de aulas previstas para o desenvolvimento da Situação de Aprendizagem. O plano deve conter exatamente a quantidade de carga horária e aulas previstas no Item Cabeçalho. Informações do Curso. 
    
    Não utilizar a marcação <br> para quebra de linha
    Obedecer a seguinte formatação da tabela e adequar seguindo o modelo para a quantidade de capacidades:
    
| Horas/Aulas e Data    | Capacidades| Conhecimentos | Estratégias | Recursos e ambientes pedagógicos | Critérios de Avaliação   | Instrumento de Avaliação | Referências |
|-----------------------|------------|---------------|-------------|----------------------------------|--------------------------|--------------------------|-------------|
| XX horas - DD/MM/AAAA |[capacidade]|               |             |                                  |[critério crítico]        |                          |             |
|                       |            |               |             |                                  |[critério desejável]      |                          |             |
| XX horas - DD/MM/AAAA |[capacidade]|               |             |                                  |[critério crítico]        |                          |             |
|                       |            |               |             |                                  |[critério desejável]      |                          |             |

]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n

## Perguntas Mediadoras:
[
    - Elabore 5 pergundas mediadoras de acordo com a situação de aprendizagem propostas.
    - Considere as seguintes diretrizes para a elaboração de perguntas mediadoras, usando como base a Metodologia SENAI de Educação Profissional:
        Contextualização: As perguntas devem ser relacionadas ao contexto real de trabalho da ocupação, fazendo ligações com o que o aluno irá vivenciar no seu dia a dia profissional.
        Desafio: As perguntas devem desafiar o aluno a pensar além do básico, a buscar soluções criativas, a analisar diferentes perspectivas e a conectar os conhecimentos aprendidos com novas situações.
        Integração: As perguntas devem promover a integração entre teoria e prática, incentivando o aluno a aplicar o conhecimento em situações concretas.
        Abordagem: As perguntas devem ter uma abordagem que estimule o diálogo, a participação ativa e a colaboração entre os alunos.
        Níveis Cognitivos: As perguntas devem ser formuladas de forma a atingir diferentes níveis cognitivos da taxonomia de Bloom (lembrar, entender, aplicar, analisar, avaliar e criar).
]
"""
modeloPlanoAulaAtual="""

## Plano de Aula:
[
    Tabela contendo:
    - Colulas:
        -Nº horas/aula e data:
            [carga horária em horas e data da aula no formato (DD/MM/AAAA)]
        -Capacidades a serem desenvolvidas:
            [ Listar as capacidades selecionadas anteriormente para a situação de aprendizagem.]
        -Conhecimentos relacionados:
            [ Listar os conhecimentos selecionados anteriormente para o desenvolvimento da situação de aprendizagem.]
        -Estratégias de ensino e instrumentos de avaliação:
            [ Por exemplo:
                - Exposição dialogada: explorar sobre os principais conhecimentos associados ao mercado no que tange às normas e legislações.
                - Simulação: elaboração e aplicação de ficha de análise de investigação de acidentes.
                - Dinâmica de grupo: conversando com as famílias das vítimas de acidente de trabalho.
            ]
        -Recursos e ambientes pedagógicos:
            [Computador, internet, notion, Microsoft Teams, Microsoft Learn, Plataforma de Gamificação Quizziz, Forms, Mentimeter, Kahoot, entre outros.]
        -Critérios de Avaliação:
            [ 
                Listar os critérios de avaliação, elaborados anteriormente no item Critérios de Avaliação necessários para a avaliação da situação de aprendizagem proposta.
                Para cada critério de avaliação que for selecionado para ser trabalhado na aula, deve ser indicado todos os critérios de avaliação que foram definidos anteriormente.
            ]
        -Instrumentos de Avaliação:
            [ 
                O instrumento de avaliação é a ferramenta utilizada para medir e analisar o desempenho dos alunos em relação aos critérios de avaliação definidos.
                Ele pode ser de diversas formas, como:
                    - Provas: escritas, práticas ou orais, que avaliam o conhecimento teórico e prático dos alunos.
                    - Trabalhos: individuais ou em grupo, que exigem pesquisa, análise e aplicação dos conhecimentos.
                    - Portfólios: um conjunto de trabalhos, projetos e evidências que demonstram o desenvolvimento do aluno ao longo do curso.
                    - Observação: do professor sobre o desempenho do aluno em sala de aula, durante as atividades práticas ou em projetos.
                    - Autoavaliação: a própria análise do aluno sobre seu próprio aprendizado e desenvolvimento.
            ]
        -Referências bibliográficas de acordo com o plano de curso:
            [livros, apostilas, sites, blogs, artigos, etc]
            [incluir referências de acordo com as indicadas na Unidade Curricular e também indicar referências externas, que sejam pertinentes ao plano de aula e a unidade curricular.]
            [toda aula deve ter pelo menos uma referência bibliográfica.]
    
    O Plano de Aula deve contemplar toda a carga horária e número de aulas previstas para o desenvolvimento da Situação de Aprendizagem. O plano deve conter exatamente a quantidade de carga horária e aulas previstas no Item Cabeçalho. Informações do Curso. 
    
    Não utilizar a marcação <br> para quebra de linha
    Obedecer rigorosamente a seguinte formatação da tabela e adequar seguindo o modelo para a quantidade de capacidades:
    
| Horas/Aulas e Data | Capacidades | Conhecimentos | Estratégias | Recursos e ambientes pedagógicos | Critérios de Avaliação | Instrumento de Avaliação | Referências |
|:---|:---|:---|:---|:---|:---|:---|:---|
| XX horas - DD/MM/AAAA |[capacidade]|   |   |   |[critérios de avaliação] |   |   |
| XX horas - DD/MM/AAAA |[capacidade]|   |   |   |[critérios de avaliação] |   |   |
 
]

## Perguntas Mediadoras:
[
    - Elabore 5 pergundas mediadoras de acordo com a situação de aprendizagem propostas.
    - Considere as seguintes diretrizes para a elaboração de perguntas mediadoras, usando como base a Metodologia SENAI de Educação Profissional:
        Contextualização: As perguntas devem ser relacionadas ao contexto real de trabalho da ocupação, fazendo ligações com o que o aluno irá vivenciar no seu dia a dia profissional.
        Desafio: As perguntas devem desafiar o aluno a pensar além do básico, a buscar soluções criativas, a analisar diferentes perspectivas e a conectar os conhecimentos aprendidos com novas situações.
        Integração: As perguntas devem promover a integração entre teoria e prática, incentivando o aluno a aplicar o conhecimento em situações concretas.
        Abordagem: As perguntas devem ter uma abordagem que estimule o diálogo, a participação ativa e a colaboração entre os alunos.
        Níveis Cognitivos: As perguntas devem ser formuladas de forma a atingir diferentes níveis cognitivos da taxonomia de Bloom (lembrar, entender, aplicar, analisar, avaliar e criar).
]

Incluir ao final deste bloco:⚠️ Este Plano de Ensino foi gerado por IA e deve ser avaliado por um docente.\n\n
"""