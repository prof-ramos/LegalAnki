# Analise dos Prompts Utilizados no LegalAnki

| Campo  | Valor            |
| ------ | ---------------- |
| Data   | 2026-02-08       |
| Escopo | `src/legal_anki/prompts/system.py`, `generator.py` |

---

## 1. Visao Geral da Arquitetura de Prompts

O LegalAnki utiliza uma arquitetura de prompts em duas camadas:

| Camada         | Arquivo                  | Funcao                                      |
| -------------- | ------------------------ | ------------------------------------------- |
| System Prompt  | `prompts/system.py`      | Instrucoes de comportamento e formato ao LLM |
| User Message   | `generator.py` (L109-125)| Conteudo juridico + parametros do usuario    |

O fluxo completo:

```
build_system_prompt(include_legal_basis, difficulty)
        +
_build_user_message(text, topic, card_type, max_cards)
        |
        v
  OpenAI Structured Outputs (GPT-4o)
        |
        v
  CardResponse (Pydantic) -> validacao -> pos-processamento
```

---

## 2. Analise do System Prompt (`SYSTEM_PROMPT_BASE`)

### 2.1 Definicao de Persona

```
Voce e um especialista em Direito Constitucional brasileiro, professor experiente focado em
preparacao para concursos publicos de alto nivel (Magistratura, MP, Defensoria, Advocacia Publica).
```

**Pontos positivos:**
- Define um papel claro e especifico (professor de Direito Constitucional)
- Contextualiza o nivel de exigencia (concursos de alto nivel)
- Lista os concursos-alvo, ancorando o registro de linguagem esperado

**Oportunidades de melhoria:**
- Poderia explicitar o *tom* desejado (ex.: linguagem tecnica, objetiva, sem coloquialismos)
- Nao menciona que o LLM deve evitar alucinacoes de artigos ou sumulas inexistentes — ponto critico para conteudo juridico
- Considerar adicionar: *"Caso nao tenha certeza de um fundamento legal, indique isso explicitamente em vez de inventar uma referencia"*

### 2.2 Regras de Conteudo

O prompt define tres regras fundamentais:

| Regra         | Descricao                              | Avaliacao |
| ------------- | -------------------------------------- | --------- |
| Atomicidade   | Um conceito por card                   | Bem definida, com exemplos positivo e negativo |
| Clareza       | Perguntas claras, linguagem tecnica    | Adequada, mas sem exemplos concretos |
| Completude    | Respostas concisas mas completas       | Vaga — nao define limites de tamanho |

**Pontos positivos:**
- A regra de atomicidade inclui exemplos contrastivos (certo vs. errado), o que e uma tecnica eficaz de prompt engineering
- Alinhado com as melhores praticas de criacao de flashcards (principio do minimo de informacao)

**Oportunidades de melhoria:**
- **Clareza**: falta exemplo contrastivo como nas outras regras
- **Completude**: deveria definir limites praticos (ex.: "respostas entre 1 e 4 frases") para evitar cards com respostas excessivamente longas
- Nao ha regra explicita contra **cards duplicados** ou muito semelhantes em um mesmo lote
- Nao ha instrucao sobre **ordenacao logica** dos cards gerados (do basico ao avancado)

### 2.3 Instrucao de Fundamento Legal (`LEGAL_BASIS_INSTRUCTION`)

```
SEMPRE inclua o fundamento legal (artigo, inciso, sumula, ADI, ADC, RE, etc.)
no campo 'extra.fundamento' ou 'extra.fundamento_legal'
```

**Pontos positivos:**
- Instrucao clara e direta
- Fornece exemplos concretos de formatacao (Art. 5o, LXIII, CF/88)
- Diferencia tipos de fundamento (artigos, sumulas, julgados)
- E modular — pode ser ativada/desativada via parametro `include_legal_basis`

**Oportunidades de melhoria:**
- Nao instrui o LLM sobre **o que fazer quando nao houver fundamento legal claro** para o conteudo fornecido
- Poderia incluir instrucao para citar a fonte normativa completa (ex.: "CF/88" vs. "CRFB/1988")
- Nao menciona a distincao entre norma vigente e norma revogada — relevante para concursos

### 2.4 Tipos de Card

O prompt define 4 tipos com instrucoes especificas:

| Tipo             | Instrucoes no Prompt                      | Alinhamento com Validator |
| ---------------- | ----------------------------------------- | ------------------------- |
| `basic`          | Pergunta direta, conceitos, definicoes    | Validacao basica (front/back minimos) |
| `cloze`          | Sintaxe `{{c1::texto}}`, max 2-3 clozes  | Valida presenca de `{{c1::` ou `{{c2::` |
| `questao`        | Estilo concurso, obrigatorio banca/ano    | Valida presenca de `banca` em extra |
| `jurisprudencia` | Sumulas/teses, obrigatorio tribunal/tema  | Valida presenca de `tribunal` em extra |

**Pontos positivos:**
- Cada tipo tem regras claras e campos obrigatorios
- Boa correspondencia entre o que o prompt exige e o que o validator verifica
- A sintaxe cloze e documentada com a notacao correta do Anki

**Oportunidades de melhoria:**
- O prompt diz "OBRIGATORIO: preencher extra.banca, extra.ano" para `questao`, mas o validator (`validators.py:66`) so verifica `banca`, nao `ano` — **desalinhamento**
- Para `jurisprudencia`, o prompt diz "OBRIGATORIO: extra.tribunal, extra.tema", mas o validator (`validators.py:71`) so verifica `tribunal`, nao `tema` — **desalinhamento**
- O prompt menciona "Maximo de 2-3 clozes por card" mas nao ha validacao para isso
- Nao ha instrucao sobre o que fazer com cards do tipo `questao` quando banca/ano nao estao no texto fonte

### 2.5 Formato de Saida

O prompt especifica campos e estrutura JSON, reforçado pelo uso de **Structured Outputs** da OpenAI com modelo Pydantic.

**Pontos positivos:**
- Dupla garantia: instrucao no prompt + schema Pydantic forçado via API
- Campos `extra` documentados por tipo de card
- O uso de `response_format=CardResponse` elimina problemas de parsing JSON

**Oportunidades de melhoria:**
- A documentacao dos campos extra no prompt usa `{{ }}` com escape para formatacao Python, o que pode gerar confusao visual para manutencao
- Poderia incluir exemplo de card para cada tipo (atualmente so ha 2 exemplos few-shot: `basic` e `jurisprudencia`)

### 2.6 Sistema de Tags

```
Use tags hierarquicas quando apropriado:
- direito_constitucional::direitos_fundamentais::liberdade
- direito_constitucional::organizacao_estado::federalismo
```

**Pontos positivos:**
- Usa convencao hierarquica do Anki (separador `::`)
- Exige tag de dificuldade obrigatoria
- Tags sao normalizadas em pos-processamento (`utils.normalize_tags`)

**Oportunidades de melhoria:**
- O prompt usa `::` como separador de tags hierarquicas, mas o pos-processamento em `_postprocess_cards` (`generator.py:150`) gera `dificuldade_medio` com underscore em vez de `dificuldade::medio` — **inconsistencia** com o padrao hierarquico instruido no prompt
- Nao define um vocabulario controlado de tags, o que pode gerar tags redundantes ou inconsistentes entre lotes (ex.: "direitos_fundamentais" vs. "direito_fundamental" vs. "dir_fundamentais")
- Considerar fornecer uma lista fechada de tags de primeiro nivel no prompt

---

## 3. Analise do User Message (`_build_user_message`)

```python
f"""Gere ate {max_cards} flashcards Anki sobre o seguinte conteudo:

**Topico**: {topic}

---
{text}
---

{type_instruction}

Retorne os cards em formato JSON conforme especificado."""
```

**Pontos positivos:**
- Estrutura clara com delimitadores (`---`) para isolar o conteudo-fonte
- Passa os parametros essenciais (max_cards, topic, type_instruction)
- Conciso e direto

**Oportunidades de melhoria:**
- Nao repete a instrucao de dificuldade no user message — o LLM precisa lembrar do system prompt
- Nao contextualiza o **tipo de conteudo** (lei, doutrina, questao, sumula), o que ajudaria o LLM a calibrar o tipo de card automaticamente no modo `auto`
- Quando `card_type="auto"`, o prompt nao orienta o LLM sobre como decidir o tipo — poderia incluir heuristicas (ex.: "Se o texto contiver alternativas A/B/C/D, gere cards tipo questao")
- O `type_instruction` e uma string vazia quando `card_type="auto"`, resultando em linhas em branco extras no prompt — esteticamente menor, mas pode adicionar ruido

---

## 4. Analise dos Exemplos Few-Shot (`EXAMPLE_CARDS`)

Dois exemplos sao definidos mas **nao sao utilizados** no prompt atual:

```python
# Exemplos de cards para few-shot learning (opcional)
EXAMPLE_CARDS = [...]
```

**Observacao critica:** Os exemplos estao definidos em `prompts/system.py` (L102-130) mas a funcao `build_system_prompt()` **nao os incorpora** no prompt enviado ao LLM. Eles sao codigo morto no fluxo atual.

**Impacto:**
- O LLM nao recebe exemplos concretos de output esperado, dependendo apenas de instrucoes textuais
- Few-shot examples sao uma das tecnicas mais eficazes para guiar LLMs — sua ausencia pode reduzir a consistencia dos outputs
- O PRD (secao 7.4) menciona "Exemplos de cards validos" como parte da estrategia de prompt

**Recomendacao:** Incorporar os exemplos no system prompt, idealmente com um exemplo para cada tipo de card (atualmente so existem `basic` e `jurisprudencia`).

---

## 5. Alinhamento Prompt vs. Validacao

| Aspecto                    | Instrucao no Prompt | Validacao em `validators.py` | Status           |
| -------------------------- | ------------------- | ---------------------------- | ---------------- |
| Front minimo               | "clara e direta"    | `min_front_length=10`        | Parcial          |
| Back minimo                | "concisa mas completa" | `min_back_length=5`       | Parcial          |
| Tags obrigatorias          | Sim                 | `if not card.tags`           | Alinhado         |
| Cloze com marcacao         | `{{c1::texto}}`     | Verifica `{{c1::` ou `{{c2::` | Alinhado       |
| Questao com banca          | Obrigatorio         | Verifica `extra.banca`       | Alinhado         |
| Questao com ano            | Obrigatorio         | **Nao verificado**           | **Desalinhado**  |
| Jurisprudencia com tribunal| Obrigatorio         | Verifica `extra.tribunal`    | Alinhado         |
| Jurisprudencia com tema    | Obrigatorio         | **Nao verificado**           | **Desalinhado**  |
| Fundamento legal           | Condicional         | `_check_legal_basis()`       | Alinhado         |
| Max 2-3 clozes por card    | Sim                 | **Nao verificado**           | **Desalinhado**  |
| Atomicidade                | Sim                 | **Nao verificado**           | Nao verificavel  |

---

## 6. Tecnicas de Prompt Engineering Utilizadas

| Tecnica                  | Presente? | Onde                              | Eficacia        |
| ------------------------ | --------- | --------------------------------- | --------------- |
| Role prompting           | Sim       | Abertura do system prompt         | Alta            |
| Structured output        | Sim       | Pydantic + API Structured Outputs | Muito alta      |
| Exemplos contrastivos    | Parcial   | So na regra de atomicidade        | Media           |
| Few-shot examples        | Definido  | `EXAMPLE_CARDS` - **nao usado**   | Nenhuma (morto) |
| Delimitadores de conteudo| Sim       | `---` no user message             | Alta            |
| Instrucoes condicionais  | Sim       | `include_legal_basis` modular     | Alta            |
| Chain of thought         | Nao       | -                                 | N/A             |
| Negative prompting       | Parcial   | Exemplo negativo na atomicidade   | Media           |
| Temperature/top_p control| Nao       | Usa defaults da API               | N/A             |

---

## 7. Riscos Identificados

### 7.1 Alucinacao de Fundamentos Legais (Risco Alto)

O prompt instrui o LLM a "SEMPRE incluir fundamento legal", mas nao instrui sobre o que fazer quando o fundamento nao e claro ou o LLM nao tem certeza. Isso incentiva alucinacoes — o LLM pode inventar artigos, sumulas ou numeros de processos inexistentes.

**Mitigacao atual:** O validator verifica a *presenca* de keywords como "art.", "sumula", etc., mas nao verifica a *corretude* do fundamento citado.

### 7.2 Inconsistencia entre Lotes (Risco Medio)

Sem vocabulario controlado de tags e sem exemplos few-shot, diferentes chamadas podem gerar tags e formatos inconsistentes para o mesmo tema.

### 7.3 Cards Longos ou Superficiais (Risco Medio)

A falta de limites concretos de tamanho (front/back) pode resultar em cards muito longos (respostas tipo "resumao") ou muito curtos (superficiais), dependendo do conteudo e do comportamento do modelo.

---

## 8. Resumo de Recomendacoes

| # | Recomendacao                                                    | Prioridade |
| - | --------------------------------------------------------------- | ---------- |
| 1 | Incorporar `EXAMPLE_CARDS` no system prompt (few-shot)          | Alta       |
| 2 | Adicionar exemplos para todos os 4 tipos de card                | Alta       |
| 3 | Adicionar instrucao anti-alucinacao para fundamentos legais     | Alta       |
| 4 | Alinhar validacao com prompt (ano em questao, tema em jurisp.)  | Media      |
| 5 | Definir limites de tamanho para front/back no prompt            | Media      |
| 6 | Corrigir inconsistencia de tags (`dificuldade_X` vs `dificuldade::X`) | Media |
| 7 | Adicionar heuristicas para modo `card_type=auto`               | Media      |
| 8 | Criar vocabulario controlado de tags de primeiro nivel          | Baixa      |
| 9 | Considerar controle de temperature para reducir variabilidade   | Baixa      |
| 10| Adicionar instrucao contra cards duplicados no mesmo lote       | Baixa      |
