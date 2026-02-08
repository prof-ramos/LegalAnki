# Arquitetura do Sistema — LegalAnki

Gerador de flashcards Anki para Direito Constitucional brasileiro via LLM (OpenAI Structured Outputs).

---

## Sumário

1. [Visão Geral de Alto Nível](#1-visão-geral-de-alto-nível)
2. [Interações de Componentes](#2-interações-de-componentes)
3. [Fluxo de Dados](#3-fluxo-de-dados)
4. [Decisões de Design e Justificativa](#4-decisões-de-design-e-justificativa)
5. [Restrições e Limitações](#5-restrições-e-limitações)

---

## 1. Visão Geral de Alto Nível

### Propósito

LegalAnki transforma conteúdo jurídico (textos, PDFs, documentos DOCX, CSVs) em flashcards Anki estruturados e tipados, utilizando um LLM (GPT-4o) com Structured Outputs para garantir conformidade com o schema JSON.

O sistema é voltado para preparação para concursos públicos de alto nível (Magistratura, MP, Defensoria, Advocacia Pública) na área de Direito Constitucional.

### Stack Tecnológica

| Camada         | Tecnologia                          | Papel                                            |
|----------------|-------------------------------------|--------------------------------------------------|
| Linguagem      | Python 3.13+                        | Linguagem principal                              |
| Deps           | `uv`                                | Gerenciamento de dependências (nunca pip)         |
| Modelos        | Pydantic v2                         | Validação e serialização de dados                |
| LLM            | OpenAI API (gpt-4o-2024-08-06)      | Geração estruturada de cards                     |
| Retry          | Tenacity                            | Backoff exponencial para erros transientes da API|
| Anki           | genanki                             | Geração de pacotes .apkg sem Anki Desktop        |
| AnkiConnect    | httpx                               | Sincronização direta com Anki Desktop (opcional) |
| Parsing        | PyMuPDF, python-docx, csv (stdlib)  | Extração de texto de múltiplos formatos          |
| Config         | pydantic-settings + python-dotenv   | Configuração via variáveis de ambiente           |
| Testes         | pytest + pytest-cov                 | Testes unitários com mocks (sem chamadas de API) |
| Lint/Format    | ruff                                | Linting e formatação de código                   |

### Mapa de Módulos

```text
src/legal_anki/
  __init__.py             # Versão via importlib.metadata
  config.py               # Settings (singleton), CardType, Difficulty (enums)
  models.py               # AnkiCard, CardResponse (Pydantic) + templates genanki
  validators.py           # Validação de negócio pós-LLM
  generator.py            # Orquestrador: chunking -> LLM -> dedup
  serializers.py          # AnkiCard -> campos genanki por tipo
  parsers.py              # Extração de texto (PDF, DOCX, CSV, TXT)
  exporters.py            # Saída: CSV, TSV, JSON, APKG
  utils.py                # slugify_tag, normalize_tags, escape_html, truncate_text
  anki_connect.py         # Cliente AnkiConnect API v6
  llm/
    protocol.py           # LLMClient (Protocol) - interface plugável
    openai_client.py      # OpenAILLMClient com retry via Tenacity
  prompts/
    system.py             # System prompt + few-shot examples
```

---

## 2. Interações de Componentes

### Diagrama de Dependências entre Módulos

```text
                           main.py
                          /   |   \
                         v    v    v
                   parsers  generator  exporters
                              |    \       |
                              v     v      v
                          prompts  llm/  serializers
                          system   |        |
                                   v        v
                               protocol   models
                               openai     config
                                  |
                                  v
                               models
                               config

    anki_connect (opcional) --> models, serializers, config
    validators  (chamado externamente) --> models, config
    utils       (transversal) --> usado por generator, exporters
```

### Responsabilidades por Módulo

#### `config.py` — Configuração Central

- Define `Settings` (pydantic-settings) carregado de `.env` no import
- Enums `CardType` (basic, basic_reversed, cloze, questao, jurisprudencia) e `Difficulty` (facil, medio, dificil)
- Singleton `settings` instanciado no import — testes devem usar mocks
- IDs de deck/modelos gerados automaticamente via `random.randrange(1<<30, 1<<31)` se não configurados

#### `models.py` — Modelos de Dados + Templates Anki

- `AnkiCard(BaseModel)`: front, back, card_type, tags, extra (dict opcional)
  - `field_validator` em front/back: strip automático + rejeição de strings vazias
- `CardResponse(BaseModel)`: wrapper com `list[AnkiCard]` — schema enviado ao LLM via Structured Outputs
- 4 fábricas de modelos genanki (`create_basic_model`, `create_cloze_model`, `create_questao_model`, `create_jurisprudencia_model`) com CSS compartilhado
- Cache em `_model_cache` via `get_model_for_card_type()` — não recria modelo a cada chamada

#### `llm/protocol.py` — Interface LLM

- `LLMClient(Protocol)` com método único `generate_structured(system_prompt, user_message, response_model) -> T`
- Permite troca transparente de provider (OpenAI -> Anthropic -> local) sem alterar código consumidor

#### `llm/openai_client.py` — Implementação OpenAI

- `OpenAILLMClient`: desabilita retry interno do SDK (`max_retries=0`), Tenacity controla
- Retry: `stop_after_attempt(3)`, `wait_exponential_jitter(initial=1, max=30, jitter=2)`
- Retenta apenas erros transientes: `APIError`, `RateLimitError`, `APIConnectionError`
- Usa `client.beta.chat.completions.parse()` para Structured Outputs
- Verifica `refusal` do modelo quando resultado é None

#### `prompts/system.py` — Engenharia de Prompt

- Prompt construído dinamicamente via `build_system_prompt(*, include_legal_basis, difficulty)`
- Template usa `str.format()` — chaves literais JSON escapadas com `{{ }}`
- Blocos condicionais: `LEGAL_BASIS_INSTRUCTION` (quando `include_legal_basis=True`)
- Bloco fixo: `ANTI_HALLUCINATION_INSTRUCTION` (sempre ativo, nunca condicional)
- Heurísticas de tipo automático (`AUTO_TYPE_HEURISTICS`): alternativas -> questao, artigo literal -> cloze, súmula/julgado -> jurisprudencia, conceito -> basic
- Vocabulário de tags padrão (`TAGS_VOCABULARY`) e 4 exemplos few-shot (um por tipo)
- Validação de `difficulty` contra `_VALID_DIFFICULTIES` antes de formatar

#### `generator.py` — Orquestrador Principal

- `generate_cards()`: ponto de entrada, aceita `llm_client` opcional para DI (injeção de dependência)
- Validação de inputs (text não vazio, topic não vazio, max_cards 1-100)
- Inicialização lazy do `OpenAILLMClient` quando `llm_client=None`
- Chunking, chamada LLM, pós-processamento e deduplicação em sequência
- `_chunk_text()`: divide em parágrafos (`\n\n`), max 50k chars por chunk
- `_deduplicate_cards()`: remove duplicatas por `front.strip().lower()`, mantém primeiro
- `_postprocess_cards()`: normaliza tags, adiciona topic tag e `dificuldade::{nível}`

#### `parsers.py` — Extração de Texto

- `parse_file(path)`: dispatch por extensão via `_PARSERS` dict
- TXT: `path.read_text(encoding="utf-8")`
- PDF: PyMuPDF `page.get_text()` por página, unido com `\n\n`
- DOCX: python-docx, parágrafos não vazios unidos com `\n\n`
- CSV: `csv.Sniffer` para detectar dialeto, células unidas com ` | ` por linha
- Erros: `ParseError` com contexto original via `raise ... from e`

#### `validators.py` — Validação de Negócio

- `validate_card()`: regras de negócio pós-LLM
  - Todos: front >= 15 chars, back >= 20 chars, tags não vazia, card_type válido
  - Cloze: requer `{{cN::}}`, máximo 3 lacunas
  - Questão: extra.banca e extra.ano obrigatórios
  - Jurisprudência: extra.tribunal e extra.tema obrigatórios
  - Fundamento legal: verifica extra.fundamento/fundamento_legal OU keywords no back
- `validate_cards_batch()`: itera lista, pode coletar erros (`skip_invalid=True`) ou falhar rápido
- `CardValidationError`: carrega `.errors` (lista de strings) e `.card` opcional

#### `serializers.py` — Mapeamento Card -> Campos Genanki

- `map_card_to_fields(card)`: retorna `list[str]` na ordem esperada pelo modelo genanki
  - Cloze: `[front, extra.fundamento]`
  - Questão: `[front, back, banca, ano, cargo, fundamento]`
  - Jurisprudência: `[front, back, tribunal, data_julgamento, tema, fundamento_legal]`
  - Basic/Basic_Reversed: `[front, back]`

#### `exporters.py` — Formatos de Saída

- CSV (default): separador `;` (padrão Excel BR), `QUOTE_ALL`, sanitiza newlines
- TSV: tab-separated, formato simples para importação direta no Anki
- JSON: estrutura completa + metadata (versão, modelo, timestamp)
- APKG: `genanki.Package` com deck/notes montados via serializers
- APKG Base64: variante em-memória via `BytesIO` para APIs/bots sem filesystem
- `export_cards()`: função unificada que delega por formato

#### `anki_connect.py` — Sincronização Direta (Opcional)

- `AnkiConnectClient`: POST para `http://localhost:8765` (API v6)
- Operações: `is_available`, `create_deck`, `add_note`, `add_notes_batch`, `sync`
- `add_card()` e `add_cards_batch()`: convertem `AnkiCard` para formato AnkiConnect via serializers
- Erros: `AnkiConnectError` com contexto de conexão/API

#### `utils.py` — Utilitários Transversais

- `slugify_tag()`: remove acentos (NFKD), substitui espaços por `_`, remove caracteres especiais, preserva `::` (separador hierárquico Anki) tratando cada segmento isoladamente
- `normalize_tags()`: slugify + dedup mantendo ordem
- `escape_html()`: escapa `& < > " '` para templates HTML do Anki
- `truncate_text()`: trunca com sufixo `...`

---

## 3. Fluxo de Dados

### 3.1 Pipeline Principal (CLI)

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           main.py (CLI)                             │
│  args: input, --topic, --difficulty, --max-cards, --output          │
└──────────┬────────────────────────────────┬─────────────────────────┘
           │                                │
           v                                │
 ┌─────────────────┐                        │
 │   parsers.py    │                        │
 │  parse_file()   │                        │
 │  TXT/PDF/DOCX/  │                        │
 │  CSV -> str     │                        │
 └────────┬────────┘                        │
          │ texto puro                      │
          v                                 │
 ┌──────────────────────────────────────┐   │
 │          generator.py                │   │
 │  generate_cards(text, topic, ...)    │   │
 │                                      │   │
 │  1. Valida inputs                    │   │
 │  2. Inicializa LLM client (lazy)    │   │
 │  3. Constrói system prompt           │   │
 │  4. Divide texto em chunks (~50k)    │   │
 │  5. Para cada chunk:                 │   │
 │     └─> _call_llm() -> [AnkiCard]   │   │
 │  6. Pós-processamento (tags, topic)  │   │
 │  7. Deduplicação (case-insensitive)  │   │
 │  8. Retorna cards[:max_cards]        │   │
 └────────┬─────────────────────────────┘   │
          │ list[AnkiCard]                  │
          v                                 v
 ┌────────────────────────────────────────────┐
 │              exporters.py                  │
 │  export_to_csv(cards, output_path)         │
 │  -> arquivo .csv com ";" separator         │
 └────────────────────────────────────────────┘
```

### 3.2 Fluxo Interno do Generator (Chunking + LLM)

```text
texto de entrada (potencialmente longo)
          │
          v
   _chunk_text(text, max_chars=50_000)
          │
          ├── len(text) <= 50k? ──> [text]  (chunk único)
          │
          └── split em \n\n (parágrafos)
              acumula até < 50k chars
              ──> [chunk_1, chunk_2, ..., chunk_N]
                      │
                      │  distribui max_cards entre chunks
                      │  cards_per_chunk = max_cards // N
                      │  remainder distribuído nos primeiros chunks
                      │
                      v
              ┌───────────────────────────────┐
              │  Para cada chunk_i:            │
              │                               │
              │  user_msg = _build_user_msg(   │
              │    chunk_i, topic,             │
              │    card_type, n_cards)         │
              │                               │
              │  llm_client.generate_structured│
              │    (system_prompt,             │
              │     user_msg,                  │
              │     CardResponse)              │
              │       │                        │
              │       └─> CardResponse.cards   │
              └───────────────┬───────────────┘
                              │
                              v  (agregação de todos os chunks)
                     raw_cards: list[AnkiCard]
                              │
                              v
                    _postprocess_cards()
                    - normalize_tags (slugify + dedup)
                    - insert topic tag em posição 0
                    - append "dificuldade::{nível}"
                              │
                              v
                    _deduplicate_cards()
                    - key = front.strip().lower()
                    - mantém primeiro, descarta duplicatas
                              │
                              v
                    cards[:max_cards]
```

### 3.3 Fluxo da Chamada LLM (com Retry)

```text
  generator._call_llm()
         │
         v
  OpenAILLMClient.generate_structured()
         │
         v
  Tenacity Retrying
  ├── stop: after 3 attempts
  ├── wait: exponential jitter (1s initial, 30s max, 2s jitter)
  ├── retry on: APIError | RateLimitError | APIConnectionError
  └── before_sleep: logger.warning com attempt_number
         │
         v
  _call_openai_api()
         │
         v
  client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[system, user],
    response_format=CardResponse,  ← Structured Outputs (schema Pydantic)
    temperature=0.7
  )
         │
         v
  response.choices[0].message.parsed
         │
         ├── parsed != None ──> return CardResponse
         │
         └── parsed == None
             ├── refusal? ──> ValueError("LLM recusou gerar resposta: ...")
             └── else     ──> ValueError("LLM não retornou resposta válida")
```

### 3.4 Fluxo de Exportação APKG

```text
  list[AnkiCard]
         │
         v
  export_to_apkg(cards, deck_name, output_path)
         │
         v
  genanki.Deck(deck_id=settings.anki_deck_id, name=deck_name)
         │
         v
  Para cada card:
  ├── model = get_model_for_card_type(card.card_type)  ← cache
  ├── fields = map_card_to_fields(card)                ← serializers.py
  ├── note = genanki.Note(model, fields, tags)
  └── deck.add_note(note)
         │
         v
  genanki.Package(deck).write_to_file(output_path)
         │
         v
  arquivo .apkg (SQLite compactado, importável no Anki Desktop)
```

### 3.5 Construção do System Prompt

```text
  build_system_prompt(include_legal_basis=True, difficulty="medio")
         │
         v
  Validação: difficulty in {"facil", "medio", "dificil"}
         │
         v
  SYSTEM_PROMPT_BASE.format(
    legal_basis_instruction = LEGAL_BASIS_INSTRUCTION | ""    ← condicional
    anti_hallucination_instruction = ANTI_HALLUCINATION_INSTRUCTION  ← sempre
    auto_type_heuristics = AUTO_TYPE_HEURISTICS               ← sempre
    tags_vocabulary = TAGS_VOCABULARY                          ← sempre
    dificuldade = difficulty                                   ← parâmetro
    examples = _format_examples()                              ← 4 few-shot cards
  )
         │
         v
  Prompt final (~2500-3000 tokens) com:
  1. Papel: especialista em Direito Constitucional
  2. Regras de conteúdo (atomicidade, clareza, completude)
  3. Instrução de fundamento legal (condicional)
  4. Anti-alucinação (fixo)
  5. Tipos de card com regras por tipo
  6. Heurísticas de seleção automática de tipo
  7. Formato de saída e campos extra por tipo
  8. Vocabulário de tags + regra hierárquica
  9. 4 exemplos few-shot (basic, cloze, questao, jurisprudencia)
```

---

## 4. Decisões de Design e Justificativa

### 4.1 Protocol Pattern para LLM Client

**Decisão**: Usar `typing.Protocol` para definir a interface `LLMClient` em vez de uma classe abstrata (`ABC`).

**Justificativa**: Structural subtyping (duck typing estático) — qualquer classe que implemente `generate_structured(system_prompt, user_message, response_model) -> T` satisfaz o protocolo sem herança explícita. Isso simplifica testes (`MockLLMClient` não precisa herdar nada) e permite troca de providers (OpenAI -> Anthropic -> modelo local) sem acoplamento. O `generator.py` depende apenas do protocolo, não da implementação.

### 4.2 Structured Outputs em vez de Parsing Manual

**Decisão**: Usar `client.beta.chat.completions.parse()` com `response_format=CardResponse` (modelo Pydantic) em vez de extrair JSON de texto livre.

**Justificativa**: O OpenAI Structured Outputs garante que a resposta do LLM obedece ao schema JSON derivado do modelo Pydantic. Isso elimina erros de parsing, campos ausentes e tipos incorretos — o output já chega como instância `CardResponse` validada. Sem isso, seria necessário regex/json.loads com tratamento de erros frágil.

### 4.3 Tenacity em vez de Retry do SDK

**Decisão**: Desabilitar retry interno do SDK OpenAI (`max_retries=0`) e usar Tenacity com configuração explícita.

**Justificativa**: Controle fino sobre a estratégia de retry — backoff exponencial com jitter (`initial=1, max=30, jitter=2`), filtragem seletiva de exceções (apenas `APIError`, `RateLimitError`, `APIConnectionError`), e logging de cada tentativa via `before_sleep`. O retry do SDK não oferece esse nível de visibilidade e customização.

### 4.4 Chunking por Parágrafos com Limite de 50k chars

**Decisão**: Dividir textos longos em chunks de até 50k caracteres, quebrando em limites de parágrafo (`\n\n`).

**Justificativa**:

- 50k chars ≈ 12.5k tokens para português (~4 chars/token)
- Deixa margem para system prompt (~3k tokens) e resposta (~4k tokens) dentro do context window
- Quebra em parágrafos preserva contexto semântico (não corta frases)
- Distribuição proporcional de `max_cards` entre chunks garante cobertura uniforme
- Deduplicação ao final evita cards repetidos entre chunks adjacentes

### 4.5 Singleton Settings no Import

**Decisão**: `settings = Settings()` instanciado no nível de módulo em `config.py`.

**Justificativa**: Configuração carregada uma única vez no import, disponível globalmente. Evita overhead de recarregar `.env` em cada operação. Para testes, usar mocks (`monkeypatch`, `unittest.mock.patch`) em vez de tentar alterar o singleton — isso garante isolamento de testes sem efeitos colaterais.

### 4.6 Enums com StrEnum

**Decisão**: `CardType` e `Difficulty` herdam de `StrEnum`.

**Justificativa**: `StrEnum` permite comparação direta com strings (`card.card_type == "basic"` funciona), serialização automática em JSON, e validação de valores pelo Pydantic sem necessidade de custom validators. Elimina bugs de typo (valor inválido falha na construção do enum).

### 4.7 Cache de Modelos Genanki

**Decisão**: `_model_cache` em `models.py` armazena modelos genanki já criados, indexados por `card_type`.

**Justificativa**: Modelos genanki são objetos pesados que registram templates, CSS e IDs. Recriar a cada card desperdiçaria recursos e poderia gerar IDs inconsistentes (se `_generate_anki_id` fosse chamado novamente). O cache garante um único modelo por tipo durante a vida do processo.

### 4.8 CSV com Separador `;`

**Decisão**: Usar ponto-e-vírgula como separador no CSV default.

**Justificativa**: Padrão brasileiro para Excel, que usa `,` como separador decimal. Textos jurídicos frequentemente contêm vírgulas, o que quebraria um CSV separado por `,` mesmo com quoting.

### 4.9 Validação Separada do Prompt

**Decisão**: `validators.py` implementa regras de negócio independentes do prompt.

**Justificativa**: O prompt instrui o LLM, mas não garante obediência. A validação pós-LLM funciona como "safety net" para rejeitar cards que não atendem requisitos mínimos (comprimento, campos obrigatórios, formato cloze). Prompt e validator devem estar sincronizados — se o prompt diz "OBRIGATÓRIO", o validator deve verificar.

### 4.10 Anti-Alucinação como Bloco Fixo

**Decisão**: `ANTI_HALLUCINATION_INSTRUCTION` é sempre incluída no prompt, nunca condicionada a flags.

**Justificativa**: Em domínio jurídico, referências fabricadas (artigos inexistentes, súmulas inventadas) são danosas e silenciosas — o usuário pode não perceber o erro. A instrução orienta o LLM a preferir omissão ("CF/88" genérico) sobre fabricação ("Art. 157-A" inexistente). Condicionar isso a um flag criaria risco de desabilitar por acidente.

### 4.11 Bullet Points no Prompt em vez de Numeração

**Decisão**: Regras no prompt usam bullet points em vez de listas numeradas.

**Justificativa**: Blocos condicionais do prompt (ex: `legal_basis_instruction`) podem ser string vazia. Com numeração fixa, a omissão de um bloco criaria gaps ("1, 2, 4, 5") que confundem o LLM. Bullet points evitam esse problema.

### 4.12 Lazy Import do OpenAI Client

**Decisão**: `OpenAILLMClient` é importado dentro de `generate_cards()` apenas quando `llm_client=None`.

**Justificativa**: Evita que `import openai` falhe quando o pacote não está instalado ou `OPENAI_API_KEY` não está configurada — útil para testes que injetam `MockLLMClient`. O import acontece apenas no caminho que realmente precisa do client.

### 4.13 Injeção de Dependência via Parâmetro

**Decisão**: `generate_cards()` aceita `llm_client` opcional.

**Justificativa**: Permite testes sem chamadas de API (injetando `MockLLMClient`), troca de provider em runtime, e controle fino sobre configuração do client. Se não fornecido, cria `OpenAILLMClient` com settings do singleton — zero-config para uso normal.

---

## 5. Restrições e Limitações

### 5.1 Dependências Externas

| Restrição | Impacto | Mitigação |
|-----------|---------|-----------|
| Requer `OPENAI_API_KEY` válida | Sem API key, geração falha | Validação explícita em `generate_cards()` com mensagem clara |
| Dependente do modelo `gpt-4o-2024-08-06` | Model deprecation pode quebrar | Configurável via `OPENAI_MODEL` em `.env` |
| AnkiConnect requer Anki Desktop rodando | Sincronização direta indisponível se Anki fechado | AnkiConnect é opcional; exportação APKG/CSV funciona standalone |
| PyMuPDF para PDFs (sem OCR) | PDFs escaneados (imagem) não são extraídos | `ParseError` explícito: "pode requerer OCR" |

### 5.2 Limites de Processamento

| Limite | Valor | Razão |
|--------|-------|-------|
| Max cards por chamada | 100 | Validação em `generate_cards()` |
| Max chars por chunk | 50.000 | ~12.5k tokens, margem para prompt+resposta |
| Max clozes por card | 3 | Regra de validação para evitar cards confusos |
| Min front length | 15 chars | Garantir pergunta minimamente informativa |
| Min back length | 20 chars | Garantir resposta minimamente completa |
| Max CLI cards | 1.000 | Validação no argparser de `main.py` |

### 5.3 Limitações do LLM

- **Alucinação**: Mesmo com `ANTI_HALLUCINATION_INSTRUCTION`, o LLM pode fabricar referências legais. A mitigação é instrucional, não determinística.
- **Qualidade variável**: Cards gerados dependem da qualidade do texto de entrada e da capacidade do modelo. Textos muito curtos ou vagos produzem cards fracos.
- **Tipo automático**: As heurísticas de seleção de tipo (`AUTO_TYPE_HEURISTICS`) são orientações ao LLM, não regras determinísticas. O LLM pode escolher tipos não ideais.
- **Idioma fixo**: O prompt e os exemplos few-shot são em português brasileiro para Direito Constitucional. Uso em outros idiomas ou áreas jurídicas requer adaptação do prompt.

### 5.4 Limitações de Formato

- **basic_reversed**: Existe no enum `CardType` e no factory `_MODEL_FACTORY`, mas o LLM não gera esse tipo — é usado apenas para importação/exportação manual.
- **CSV sanitiza newlines**: Quebras de linha no front/back são substituídas por espaços. Formatação rica do texto original é perdida no CSV/TSV.
- **APKG base64**: Útil para APIs sem filesystem, mas o tamanho em base64 é ~33% maior que o binário original.
- **TSV simplificado**: Exporta apenas front, back e tags — não inclui tipo nem extra.

### 5.5 Limitações Arquiteturais

- **Singleton settings**: Não permite múltiplas configurações simultâneas no mesmo processo. Cenários multi-tenant precisariam de refatoração para DI completa.
- **Processamento síncrono**: Chunks são processados sequencialmente. Para textos muito longos com muitos chunks, não há paralelismo nas chamadas ao LLM.
- **Deduplicação simples**: Baseada apenas no front (case-insensitive). Cards com frentes similares mas não idênticas não são detectados como duplicatas. Não usa similaridade semântica.
- **Sem persistência**: Não há banco de dados ou cache de cards gerados. Cada execução é independente. Reprocessar o mesmo texto gera novos cards (possivelmente diferentes).
- **Sem versionamento de prompt**: Alterações no prompt não são rastreadas. Não há mecanismo para comparar qualidade entre versões do prompt.

### 5.6 Hierarquia de Exceções

```text
Exception
├── ParseError              (parsers.py)    — erro na extração de texto
├── CardGenerationError     (generator.py)  — erro na geração via LLM
├── CardValidationError     (validators.py) — card inválido pós-LLM
│   attrs: .errors (list[str]), .card (AnkiCard | None)
├── ExportError             (exporters.py)  — erro na escrita de arquivo
└── AnkiConnectError        (anki_connect.py) — erro de comunicação
```

Todas seguem o padrão `raise CustomError(...) from e` para preservar a cadeia de causas.
