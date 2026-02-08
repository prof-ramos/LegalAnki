## 1. Visão geral do produto

Skill/serviço que recebe conteúdo jurídico (leis, PDFs de aula, questões, jurisprudência) e gera automaticamente flashcards Anki otimizados para **Direito Constitucional para concursos**, com export em TSV, JSON e `.apkg`, além de opção de envio direto via AnkiConnect.[1][2]

- Público: concurseiros (OAB, magistratura, MP, delegados), estudantes de Direito e professores.[3]
- Forma de uso: embutido em agentes (Context7/MCP), bots (Discord/Telegram) ou scripts locais, recebendo texto e devolvendo cards prontos para Anki.[2][3]

## 2. Objetivos e sucesso

**Objetivos principais**:[4][3]

- Automatizar a criação de cards Anki de alta qualidade, reduzindo tempo de preparação de material.
- Garantir cards atomizados, com fundamento legal explícito e, quando aplicável, jurisprudência recente do STF/STJ.
- Permitir criação em massa (dezenas/centenas) a partir de uma única fonte (aula, lei, caderno de questões).

**Métricas de sucesso**:[5][6]

- ≥ 80% dos cards gerados aprovados pelo professor sem edição substancial.
- Tempo médio para gerar e importar um deck de 50 cards ≤ 5 minutos.
- Aderência: ≥ 90% dos cards de “jurisprudência” contêm tese, tribunal e ano.

## 3. Escopo funcional

**Incluído**:[7][8]

- Geração de cards a partir de texto bruto (leis, doutrina resumida, questões de concurso, súmulas, informativos).
- Tipos de card:
  - `basic` (pergunta e resposta diretas).
  - `cloze` (conceitos, definições, artigos).
  - `jurisprudencia` (tese + tribunal + ano + referência).
  - `questao_concurso` (enunciado, alternativa correta/comentário, fundamento, banca/ano).
- Controle de **dificuldade** (`facil`, `medio`, `dificil`, `OAB`, `magistratura`) e **topic** (ex.: “controle de constitucionalidade”).
- Export:
  - TSV (front, back, tags).
  - JSON (estrutura completa para logs/reprocessamento).
  - `.apkg` base64 via `genanki`.
- Integração opcional com AnkiConnect (`addNote`) para enviar cards diretamente ao Anki Desktop.[9][10]

**Fora de escopo (v1)**:[8][7]

- Parsing nativo de PDFs/Word (espera-se texto já extraído pelo agente/ferramenta externa).
- Interface gráfica própria (web/app). Uso previsto via CLI, agente ou bot.
- Gestão de espaçamento (scheduling) no lado da skill (delegado ao Anki).

## 4. Requisitos detalhados

### 4.1. Entrada e parâmetros

- `content: str` – bloco de texto com o material de origem.
- `card_type: "basic" | "cloze" | "jurisprudencia" | "questao_concurso"`.
- `topic: str` – tema para tags e nome do deck.
- `difficulty: "facil" | "medio" | "dificil" | "OAB" | "magistratura"`.
- `num_cards: int` – quantidade-alvo de cards (p.ex. 5–50).
- `include_legal_basis: bool` – força inclusão de fundamento legal/jurisprudencial.

Regras de comportamento:

- Se `include_legal_basis=true`, cada card deve conter pelo menos um fundamento legal (artigo, súmula, tese) no campo `back` ou `extra.fundamento`.
- `topic` e `difficulty` geram tags normalizadas (minúsculas, sem acentos e espaços).

### 4.2. Saída

Objeto JSON com:[11][2]

- `cards: List[Card]` onde `Card` tem:
  - `front: str`
  - `back: str` (pode incluir quebras de linha e emojis utilitários como 📚 / 🏛️)
  - `tags: List[str]`
  - `extra: dict` (fundamento, tribunal, banca, ano, dificuldade, etc.).
- `exports`:
  - `tsv: str` – colunas: front, back, tags.
  - `json: str` – JSON completo serializado.
  - `apkg: str` – pacote Anki em base64.
- `metadata`:
  - `total: int`
  - `deck_name: str` – ex.: `Direito Constitucional - Direitos Fundamentais`.
  - `tags_used: List[str]`
  - `skill_version: str`, `llm_model: str`.

### 4.3. Templates e modelos Anki

- Modelo “Questão Concurso Direito”: campos `Enunciado`, `Resposta`, `Fundamento`, `Banca`, com layout HTML/CSS próprio.[12][2]
- Modelo “Jurisprudência”: `Tese`, `Tribunal`, `Ano`, `Ementa_Resumida`, `Referencia_Completa`.
- Modelo “Cloze Constitucional”: campo único `Text` com sintaxe `{{c1::...}}`.
- Mapeamento de `Card.extra` → campos do modelo sempre que o modelo tiver mais que `Front/Back`.

### 4.4. LLM / Prompt

- Uso de modelo da OpenAI via `chat.completions` com `response_format={"type": "json_object"}` para garantir estrutura séria de JSON.[13][14]
- `SYSTEM_PROMPT` com:
  - Regras de atomização (um conceito por card, respostas objetivas).
  - Ênfase em literalidade da CF/88 e jurisprudência atual STF/STJ.
  - Exemplos de cards válidos (basic, cloze, jurisprudência, questão).

## 5. Requisitos não funcionais

- Performance: gerar 20 cards em ≤ 15 segundos em cenário típico (rede estável, modelo remoto).[15][3]
- Confiabilidade: validação básica pós-LLM (campos obrigatórios, JSON válido, quantidade mínima de cards) e fallback com mensagem de erro amigável.
- Observabilidade: logs de entradas (anonimizadas quando necessário), parâmetros usados e contagem de tokens/custos.
- Extensibilidade: fácil inclusão de novos `card_type` e suporte a outras áreas (ex.: Administrativo) reaproveitando a mesma arquitetura.
- Segurança: nenhuma persistência de conteúdo sensível por padrão; uso de variáveis de ambiente para chaves de API.

## 6. Fluxos principais de uso

### Fluxo 1 – Professor/Concurseiro via agente (Context7/MCP)

1. Usuário envia trecho de aula ou lei + parâmetros (tipo, tema, dificuldade, número de cards).
2. Agente chama a skill MCP `generate_anki_cards`.
3. Skill chama LLM, valida retorno, gera deck genanki e devolve JSON + `.apkg` base64.
4. Agente oferece link/download do `.apkg` ou TSV para import no Anki.

### Fluxo 2 – Integração AnkiConnect

1. Usuário executa script local com Anki aberto e AnkiConnect ativado.
2. Script chama `generate_cards`, obtém `cards`.
3. Para cada card, envia `addNote` para AnkiConnect com `deckName` e `modelName` apropriados.[10][9]
4. Cards aparecem imediatamente no deck do Anki, sem precisar de import manual.

### Fluxo 3 – Bot Discord/Telegram

1. Usuário envia PDF/lei/questões para o bot com comando `/anki constitucional magistratura 30 cards`.
2. Bot extrai texto, chama skill, recebe `.apkg`.
3. Bot envia arquivo `.apkg` pronto para download.

## 7. Restrições, dependências e riscos

- Dependência de:
  - API da OpenAI (latência, custos, limites de uso).
  - `genanki` para geração do `.apkg`.[16][12]
  - AnkiConnect (se fluxo direto for usado).[9]
- Riscos:
  - Mudança em modelos LLM afetando estilo/qualidade; mitigação via exemplos no prompt e versionamento.
  - Alucinações de fundamentos legais/jurisprudenciais; mitigação: checks automáticos simples (ex.: padrão “Art. X, §Y, CF/88”) e revisão humana para decks “high stakes”.

Fontes
[1] Documento de requisitos de produto (PRD) — o que é e ... https://brasil.uxdesign.cc/documento-de-requisitos-de-produto-prd-o-que-%C3%A9-e-como-fazer-um-d86d03c23e8c
[2] Existe aguma SKILL (para agentes de IA) focada em gera cards para o anki? https://www.perplexity.ai/search/bd2e02cb-899c-4021-a8b6-bffb9e8f1dc4
[3] Product Requirements Document: PRD Templates and Examples https://www.altexsoft.com/blog/product-requirements-document/
[4] O que é um Documento de Requisitos de Produto (PRD)? - Banani https://www.banani.co/pt/blog/what-is-prd-product-requirements-document
[5] The Only PRD Template You Need (with Example) https://productschool.com/blog/product-strategy/product-template-requirements-document-prd
[6] Free PRD Template & Example for 2026 Software https://www.inflectra.com/Ideas/Topic/PRD-Template.aspx
[7] Documento de requisitos do produto: template de PRD grátis https://monday.com/blog/pt/desenvolvimento/template-de-prd/
[8] Modelo de Documento de Requisitos do Produto (PRD) - Miro https://miro.com/pt/modelos/documento-requisitos-produto/
[9] ~foosoft/anki-connect - Anki plugin to expose a remote API for ... https://git.sr.ht/~foosoft/anki-connect
[10] AnkiConnect.Actions.Note — anki_connect v0.1.1 - Hexdocs https://hexdocs.pm/anki_connect/AnkiConnect.Actions.Note.html
[11] Modelos gratuitos de documento de requisitos do produto | Smartsheet https://pt.smartsheet.com/content/free-product-requirements-document-template
[12] kerrickstaley/genanki: A Python 3 library for generating ... https://github.com/kerrickstaley/genanki
[13] How do I use the new JSON mode? - API https://community.openai.com/t/how-do-i-use-the-new-json-mode/475890
[14] OpenAI Chat Completions: JSON 모드 - PKGPL https://pkgpl.org/2023/11/17/openai-chat-completions-json-%EB%AA%A8%EB%93%9C/
[15] Como escrever um documento de requisitos de produto ... https://visuresolutions.com/pt/alm-guide/product-requirements-document-prd
[16] genanki/genanki/package.py at e073eba89cb7ce15e64d3d72898d2f92772e2270 · kerrickstaley/genanki https://github.com/kerrickstaley/genanki/blob/e073eba89cb7ce15e64d3d72898d2f92772e2270/genanki/package.py
[17] seu guia completo para documentos de requisitos de produto https://translate.google.com/translate?u=https%3A%2F%2Fwww.perforce.com%2Fblog%2Falm%2Fhow-write-product-requirements-document-prd&hl=pt&sl=en&tl=pt&client=srp
[18] Como escrever um Documento de Requisitos do Produto ... https://translate.google.com/translate?u=https%3A%2F%2Fwww.jamasoftware.com%2Frequirements-management-guide%2Fwriting-requirements%2Fhow-to-write-an-effective-product-requirements-document%2F&hl=pt&sl=en&tl=pt&client=srp
[19] O único modelo PRD que você precisa (com exemplo) https://translate.google.com/translate?u=https%3A%2F%2Fproductschool.com%2Fblog%2Fproduct-strategy%2Fproduct-template-requirements-document-prd&hl=pt&sl=en&tl=pt&client=srp
[20] Modelo de PRD do ClickUp https://clickup.com/pt-BR/blog/62293/modelos-de-documentos-de-requisitos-de-produtos
[21] PRD Template: Guide for Product Managers - Userpilot https://userpilot.com/blog/prd-template/
[22] Como criar um documento de requisitos do produto + modelo https://translate.google.com/translate?u=https%3A%2F%2Fwww.figma.com%2Fresource-library%2Fproduct-requirements-document%2F&hl=pt&sl=en&tl=pt&client=srp
