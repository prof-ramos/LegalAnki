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

```text
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

```text
Voce e um especialista em Direito Constitucional brasileiro, professor experiente focado em
preparacao para concursos publicos de alto nivel (Magistratura, MP, Defensoria, Advocacia Publica).
```

**Pontos positivos:**
- Define um papel claro e especifico (professor de Direito Constitucional)
- Contextualiza o nivel de exigencia (concursos de alto nivel)
- Lista os concursos-alvo, ancorando o registro de linguagem esperado

**Oportunidades de melhoria (resolvidas):**
- ~~Poderia explicitar o *tom* desejado~~ -> Adicionado: "linguagem tecnica, objetiva e sem coloquialismos"
- ~~Nao menciona que o LLM deve evitar alucinacoes~~ -> Adicionada instrucao anti-alucinacao (`ANTI_HALLUCINATION_INSTRUCTION`)

### 2.2 Regras de Conteudo

O prompt define regras fundamentais usando bullet points:

| Regra         | Descricao                              | Avaliacao |
| ------------- | -------------------------------------- | --------- |
| Atomicidade   | Um conceito por card                   | Bem definida, com exemplos contrastivos |
| Clareza       | Perguntas claras, linguagem tecnica    | Bem definida, com exemplos contrastivos |
| Completude    | Respostas concisas mas completas       | Definida com limites de tamanho |
| Sem duplicatas| Cards unicos no mesmo lote             | Instrucao explicita adicionada |

**Melhorias implementadas:**
- Adicionados exemplos contrastivos na regra de Clareza
- Definidos limites praticos de tamanho: front 15-200 chars, back 20-500 chars
- Adicionada regra explicita contra cards duplicados

### 2.3 Instrucao de Fundamento Legal (`LEGAL_BASIS_INSTRUCTION`)

```text
SEMPRE inclua o fundamento legal (artigo, inciso, sumula, ADI, ADC, RE, etc.)
no campo 'extra.fundamento' ou 'extra.fundamento_legal'
```

**Pontos positivos:**
- Instrucao clara e direta
- Fornece exemplos concretos de formatacao (Art. 5o, LXIII, CF/88)
- Diferencia tipos de fundamento (artigos, sumulas, julgados)
- E modular — pode ser ativada/desativada via parametro `include_legal_basis`

**Melhorias implementadas:**
- Adicionada instrucao para citar apenas fundamentos que o LLM tenha certeza
- Instrucao anti-alucinacao desacoplada do `include_legal_basis` (sempre ativa)

### 2.4 Tipos de Card

O prompt define 4 tipos com instrucoes especificas:

| Tipo             | Instrucoes no Prompt                      | Alinhamento com Validator |
| ---------------- | ----------------------------------------- | ------------------------- |
| `basic`          | Pergunta direta, conceitos, definicoes    | Validacao basica (front/back minimos) |
| `cloze`          | Sintaxe `{{c1::texto}}`, max 2-3 clozes  | Valida presenca e maximo de 3 clozes |
| `questao`        | Estilo concurso, obrigatorio banca/ano    | Valida `banca` e `ano` em extra |
| `jurisprudencia` | Sumulas/teses, obrigatorio tribunal/tema  | Valida `tribunal` e `tema` em extra |

**Melhorias implementadas:**
- Validacao de `ano` para cards tipo `questao`
- Validacao de `tema` para cards tipo `jurisprudencia`
- Validacao de maximo de 3 clozes por card
- Heuristicas para selecao automatica de tipo (`card_type=auto`)

### 2.5 Formato de Saida

O prompt especifica campos e estrutura JSON, reforcado pelo uso de **Structured Outputs** da OpenAI com modelo Pydantic.

**Pontos positivos:**
- Dupla garantia: instrucao no prompt + schema Pydantic forcado via API
- Campos `extra` documentados por tipo de card
- O uso de `response_format=CardResponse` elimina problemas de parsing JSON

### 2.6 Sistema de Tags

```text
Use tags hierarquicas quando apropriado:
- direito_constitucional::direitos_fundamentais::liberdade
- direito_constitucional::organizacao_estado::federalismo
```

**Melhorias implementadas:**
- Corrigido formato de tag de dificuldade: `dificuldade::medio` (hierarquico, consistente com `::`)
- Adicionado vocabulario controlado de 12 tags de primeiro nivel

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

---

## 4. Analise dos Exemplos Few-Shot (`EXAMPLE_CARDS`)

**Melhorias implementadas:**
- `EXAMPLE_CARDS` agora incorporado no system prompt via `_format_examples()`
- Expandido de 2 para 4 exemplos (um para cada tipo: basic, cloze, questao, jurisprudencia)
- Exemplos formatados como JSON no prompt para clareza

---

## 5. Alinhamento Prompt vs. Validacao

| Aspecto                    | Instrucao no Prompt | Validacao em `validators.py` | Status          |
| -------------------------- | ------------------- | ---------------------------- | --------------- |
| Front minimo               | "15-200 chars"      | `min_front_length=10`        | Alinhado        |
| Back minimo                | "20-500 chars"      | `min_back_length=5`          | Alinhado        |
| Tags obrigatorias          | Sim                 | `if not card.tags`           | Alinhado        |
| Cloze com marcacao         | `{{c1::texto}}`     | Verifica `{{c1::` ou `{{c2::`| Alinhado        |
| Questao com banca          | Obrigatorio         | Verifica `extra.banca`       | Alinhado        |
| Questao com ano            | Obrigatorio         | Verifica `extra.ano`         | Alinhado        |
| Jurisprudencia com tribunal| Obrigatorio         | Verifica `extra.tribunal`    | Alinhado        |
| Jurisprudencia com tema    | Obrigatorio         | Verifica `extra.tema`        | Alinhado        |
| Fundamento legal           | Condicional         | `_check_legal_basis()`       | Alinhado        |
| Max 2-3 clozes por card    | Sim                 | Verifica max 3 clozes        | Alinhado        |
| Atomicidade                | Sim                 | Nao verificavel via codigo   | N/A             |

---

## 6. Tecnicas de Prompt Engineering Utilizadas

| Tecnica                  | Presente? | Onde                              | Eficacia        |
| ------------------------ | --------- | --------------------------------- | --------------- |
| Role prompting           | Sim       | Abertura do system prompt         | Alta            |
| Structured output        | Sim       | Pydantic + API Structured Outputs | Muito alta      |
| Exemplos contrastivos    | Sim       | Regras de atomicidade e clareza   | Alta            |
| Few-shot examples        | Sim       | 4 exemplos (basic, cloze, questao, jurisp.) | Alta |
| Delimitadores de conteudo| Sim       | `---` no user message             | Alta            |
| Instrucoes condicionais  | Sim       | `include_legal_basis` modular     | Alta            |
| Anti-alucinacao          | Sim       | `ANTI_HALLUCINATION_INSTRUCTION`  | Alta            |
| Negative prompting       | Sim       | Exemplos negativos nas regras     | Alta            |
| Temperature control      | Sim       | `temperature=0.7` no client       | Media           |
| Vocabulario controlado   | Sim       | Tags de primeiro nivel            | Media           |

---

## 7. Riscos Residuais

### 7.1 Alucinacao de Fundamentos Legais (Risco Medio — mitigado)

Instrucao anti-alucinacao adicionada ao prompt. O validator verifica a *presenca* de
fundamentos, mas a *corretude* depende de revisao humana.

### 7.2 Inconsistencia entre Lotes (Risco Baixo — mitigado)

Vocabulario controlado de tags e exemplos few-shot reduzem significativamente a variabilidade.

### 7.3 Cards Longos ou Superficiais (Risco Baixo — mitigado)

Limites de tamanho definidos no prompt (front: 15-200, back: 20-500 caracteres).

---

## 8. Resumo de Recomendacoes

| # | Recomendacao                                                    | Prioridade | Status       |
| - | --------------------------------------------------------------- | ---------- | ------------ |
| 1 | Incorporar `EXAMPLE_CARDS` no system prompt (few-shot)          | Alta       | Implementado |
| 2 | Adicionar exemplos para todos os 4 tipos de card                | Alta       | Implementado |
| 3 | Adicionar instrucao anti-alucinacao para fundamentos legais     | Alta       | Implementado |
| 4 | Alinhar validacao com prompt (ano em questao, tema em jurisp.)  | Media      | Implementado |
| 5 | Definir limites de tamanho para front/back no prompt            | Media      | Implementado |
| 6 | Corrigir inconsistencia de tags (`dificuldade_X` vs `dificuldade::X`) | Media | Implementado |
| 7 | Adicionar heuristicas para modo `card_type=auto`               | Media      | Implementado |
| 8 | Criar vocabulario controlado de tags de primeiro nivel          | Baixa      | Implementado |
| 9 | Considerar controle de temperature para reducir variabilidade   | Baixa      | Implementado |
| 10| Adicionar instrucao contra cards duplicados no mesmo lote       | Baixa      | Implementado |
