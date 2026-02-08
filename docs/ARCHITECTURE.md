# Arquitetura do Sistema — LegalAnki

Gerador de flashcards Anki para Direito Constitucional brasileiro via LLM (OpenAI Structured Outputs).

---

## Sumario

1. [Visao Geral de Alto Nivel](#1-visao-geral-de-alto-nivel)
2. [Interacoes de Componentes](#2-interacoes-de-componentes)
3. [Fluxo de Dados](#3-fluxo-de-dados)
4. [Decisoes de Design e Justificativa](#4-decisoes-de-design-e-justificativa)
5. [Restricoes e Limitacoes](#5-restricoes-e-limitacoes)

---

## 1. Visao Geral de Alto Nivel

### Proposito

LegalAnki transforma conteudo juridico (textos, PDFs, documentos DOCX, CSVs) em flashcards Anki estruturados e tipados, utilizando um LLM (GPT-4o) com Structured Outputs para garantir conformidade com o schema JSON.

O sistema e voltado para preparacao para concursos publicos de alto nivel (Magistratura, MP, Defensoria, Advocacia Publica) na area de Direito Constitucional.

### Stack Tecnologica

| Camada         | Tecnologia                          | Papel                                            |
|----------------|-------------------------------------|--------------------------------------------------|
| Linguagem      | Python 3.13+                        | Linguagem principal                              |
| Deps           | `uv`                                | Gerenciamento de dependencias (nunca pip)         |
| Modelos        | Pydantic v2                         | Validacao e serializacao de dados                |
| LLM            | OpenAI API (gpt-4o-2024-08-06)      | Geracao estruturada de cards                     |
| Retry          | Tenacity                            | Backoff exponencial para erros transientes da API|
| Anki           | genanki                             | Geracao de pacotes .apkg sem Anki Desktop        |
| AnkiConnect    | httpx                               | Sincronizacao direta com Anki Desktop (opcional) |
| Parsing        | PyMuPDF, python-docx, csv (stdlib)  | Extracao de texto de multiplos formatos          |
| Config         | pydantic-settings + python-dotenv   | Configuracao via variaveis de ambiente           |
| Testes         | pytest + pytest-cov                 | Testes unitarios com mocks (sem chamadas de API) |
| Lint/Format    | ruff                                | Linting e formatacao de codigo                   |

### Mapa de Modulos

```
src/legal_anki/
  __init__.py             # Versao via importlib.metadata
  config.py               # Settings (singleton), CardType, Difficulty (enums)
  models.py               # AnkiCard, CardResponse (Pydantic) + templates genanki
  validators.py           # Validacao de negocio pos-LLM
  generator.py            # Orquestrador: chunking -> LLM -> dedup
  serializers.py          # AnkiCard -> campos genanki por tipo
  parsers.py              # Extracao de texto (PDF, DOCX, CSV, TXT)
  exporters.py            # Saida: CSV, TSV, JSON, APKG
  utils.py                # slugify_tag, normalize_tags, escape_html, truncate_text
  anki_connect.py         # Cliente AnkiConnect API v6
  llm/
    protocol.py           # LLMClient (Protocol) - interface plugavel
    openai_client.py      # OpenAILLMClient com retry via Tenacity
  prompts/
    system.py             # System prompt + few-shot examples
```

---

## 2. Interacoes de Componentes

### Diagrama de Dependencias entre Modulos

```
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

### Responsabilidades por Modulo

#### `config.py` — Configuracao Central
- Define `Settings` (pydantic-settings) carregado de `.env` no import
- Enums `CardType` (basic, basic_reversed, cloze, questao, jurisprudencia) e `Difficulty` (facil, medio, dificil)
- Singleton `settings` instanciado no import — testes devem usar mocks
- IDs de deck/modelos gerados automaticamente via `random.randrange(1<<30, 1<<31)` se nao configurados

#### `models.py` — Modelos de Dados + Templates Anki
- `AnkiCard(BaseModel)`: front, back, card_type, tags, extra (dict opcional)
  - `field_validator` em front/back: strip automatico + rejeicao de strings vazias
- `CardResponse(BaseModel)`: wrapper com `list[AnkiCard]` — schema enviado ao LLM via Structured Outputs
- 4 fabricas de modelos genanki (`create_basic_model`, `create_cloze_model`, `create_questao_model`, `create_jurisprudencia_model`) com CSS compartilhado
- Cache em `_model_cache` via `get_model_for_card_type()` — nao recria modelo a cada chamada

#### `llm/protocol.py` — Interface LLM
- `LLMClient(Protocol)` com metodo unico `generate_structured(system_prompt, user_message, response_model) -> T`
- Permite troca transparente de provider (OpenAI -> Anthropic -> local) sem alterar codigo consumidor

#### `llm/openai_client.py` — Implementacao OpenAI
- `OpenAILLMClient`: desabilita retry interno do SDK (`max_retries=0`), Tenacity controla
- Retry: `stop_after_attempt(3)`, `wait_exponential_jitter(initial=1, max=30, jitter=2)`
- Retenta apenas erros transientes: `APIError`, `RateLimitError`, `APIConnectionError`
- Usa `client.beta.chat.completions.parse()` para Structured Outputs
- Verifica `refusal` do modelo quando resultado e None

#### `prompts/system.py` — Engenharia de Prompt
- Prompt construido dinamicamente via `build_system_prompt(*, include_legal_basis, difficulty)`
- Template usa `str.format()` — chaves literais JSON escapadas com `{{ }}`
- Blocos condicionais: `LEGAL_BASIS_INSTRUCTION` (quando `include_legal_basis=True`)
- Bloco fixo: `ANTI_HALLUCINATION_INSTRUCTION` (sempre ativo, nunca condicional)
- Heuristicas de tipo automatico (`AUTO_TYPE_HEURISTICS`): alternativas -> questao, artigo literal -> cloze, sumula/julgado -> jurisprudencia, conceito -> basic
- Vocabulario de tags padrao (`TAGS_VOCABULARY`) e 4 exemplos few-shot (um por tipo)
- Validacao de `difficulty` contra `_VALID_DIFFICULTIES` antes de formatar

#### `generator.py` — Orquestrador Principal
- `generate_cards()`: ponto de entrada, aceita `llm_client` opcional para DI (injecao de dependencia)
- Validacao de inputs (text nao vazio, topic nao vazio, max_cards 1-100)
- Inicializacao lazy do `OpenAILLMClient` quando `llm_client=None`
- Chunking, chamada LLM, pos-processamento e deduplicacao em sequencia
- `_chunk_text()`: divide em paragrafos (`\n\n`), max 50k chars por chunk
- `_deduplicate_cards()`: remove duplicatas por `front.strip().lower()`, mantém primeiro
- `_postprocess_cards()`: normaliza tags, adiciona topic tag e `dificuldade::{nivel}`

#### `parsers.py` — Extracao de Texto
- `parse_file(path)`: dispatch por extensao via `_PARSERS` dict
- TXT: `path.read_text(encoding="utf-8")`
- PDF: PyMuPDF `page.get_text()` por pagina, unido com `\n\n`
- DOCX: python-docx, paragrafos nao vazios unidos com `\n\n`
- CSV: `csv.Sniffer` para detectar dialeto, celulas unidas com ` | ` por linha
- Erros: `ParseError` com contexto original via `raise ... from e`

#### `validators.py` — Validacao de Negocio
- `validate_card()`: regras de negocio pos-LLM
  - Todos: front >= 15 chars, back >= 20 chars, tags nao vazia, card_type valido
  - Cloze: requer `{{cN::}}`, maximo 3 lacunas
  - Questao: extra.banca e extra.ano obrigatorios
  - Jurisprudencia: extra.tribunal e extra.tema obrigatorios
  - Fundamento legal: verifica extra.fundamento/fundamento_legal OU keywords no back
- `validate_cards_batch()`: itera lista, pode coletar erros (`skip_invalid=True`) ou falhar rapido
- `CardValidationError`: carrega `.errors` (lista de strings) e `.card` opcional

#### `serializers.py` — Mapeamento Card -> Campos Genanki
- `map_card_to_fields(card)`: retorna `list[str]` na ordem esperada pelo modelo genanki
  - Cloze: `[front, extra.fundamento]`
  - Questao: `[front, back, banca, ano, cargo, fundamento]`
  - Jurisprudencia: `[front, back, tribunal, data_julgamento, tema, fundamento_legal]`
  - Basic/Basic_Reversed: `[front, back]`

#### `exporters.py` — Formatos de Saida
- CSV (default): separador `;` (padrao Excel BR), `QUOTE_ALL`, sanitiza newlines
- TSV: tab-separated, formato simples para importacao direta no Anki
- JSON: estrutura completa + metadata (versao, modelo, timestamp)
- APKG: `genanki.Package` com deck/notes montados via serializers
- APKG Base64: variante em-memoria via `BytesIO` para APIs/bots sem filesystem
- `export_cards()`: funcao unificada que delega por formato

#### `anki_connect.py` — Sincronizacao Direta (Opcional)
- `AnkiConnectClient`: POST para `http://localhost:8765` (API v6)
- Operacoes: `is_available`, `create_deck`, `add_note`, `add_notes_batch`, `sync`
- `add_card()` e `add_cards_batch()`: convertem `AnkiCard` para formato AnkiConnect via serializers
- Erros: `AnkiConnectError` com contexto de conexao/API

#### `utils.py` — Utilitarios Transversais
- `slugify_tag()`: remove acentos (NFKD), substitui espacos por `_`, remove caracteres especiais, preserva `::` (separador hierarquico Anki) tratando cada segmento isoladamente
- `normalize_tags()`: slugify + dedup mantendo ordem
- `escape_html()`: escapa `& < > " '` para templates HTML do Anki
- `truncate_text()`: trunca com sufixo `...`

---

## 3. Fluxo de Dados

### 3.1 Pipeline Principal (CLI)

```
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
 │  3. Constroi system prompt           │   │
 │  4. Divide texto em chunks (~50k)    │   │
 │  5. Para cada chunk:                 │   │
 │     └─> _call_llm() -> [AnkiCard]   │   │
 │  6. Pos-processamento (tags, topic)  │   │
 │  7. Deduplicacao (case-insensitive)  │   │
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

```
texto de entrada (potencialmente longo)
          │
          v
   _chunk_text(text, max_chars=50_000)
          │
          ├── len(text) <= 50k? ──> [text]  (chunk unico)
          │
          └── split em \n\n (paragrafos)
              acumula ate < 50k chars
              ──> [chunk_1, chunk_2, ..., chunk_N]
                      │
                      │  distribui max_cards entre chunks
                      │  cards_per_chunk = max_cards // N
                      │  remainder distribuido nos primeiros chunks
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
                              v  (agregacao de todos os chunks)
                     raw_cards: list[AnkiCard]
                              │
                              v
                    _postprocess_cards()
                    - normalize_tags (slugify + dedup)
                    - insert topic tag em posicao 0
                    - append "dificuldade::{nivel}"
                              │
                              v
                    _deduplicate_cards()
                    - key = front.strip().lower()
                    - mantem primeiro, descarta duplicatas
                              │
                              v
                    cards[:max_cards]
```

### 3.3 Fluxo da Chamada LLM (com Retry)

```
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
             └── else     ──> ValueError("LLM nao retornou resposta valida")
```

### 3.4 Fluxo de Exportacao APKG

```
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
  arquivo .apkg (SQLite compactado, importavel no Anki Desktop)
```

### 3.5 Construcao do System Prompt

```
  build_system_prompt(include_legal_basis=True, difficulty="medio")
         │
         v
  Validacao: difficulty in {"facil", "medio", "dificil"}
         │
         v
  SYSTEM_PROMPT_BASE.format(
    legal_basis_instruction = LEGAL_BASIS_INSTRUCTION | ""    ← condicional
    anti_hallucination_instruction = ANTI_HALLUCINATION_INSTRUCTION  ← sempre
    auto_type_heuristics = AUTO_TYPE_HEURISTICS               ← sempre
    tags_vocabulary = TAGS_VOCABULARY                          ← sempre
    dificuldade = difficulty                                   ← parametro
    examples = _format_examples()                              ← 4 few-shot cards
  )
         │
         v
  Prompt final (~2500-3000 tokens) com:
  1. Papel: especialista em Direito Constitucional
  2. Regras de conteudo (atomicidade, clareza, completude)
  3. Instrucao de fundamento legal (condicional)
  4. Anti-alucinacao (fixo)
  5. Tipos de card com regras por tipo
  6. Heuristicas de selecao automatica de tipo
  7. Formato de saida e campos extra por tipo
  8. Vocabulario de tags + regra hierarquica
  9. 4 exemplos few-shot (basic, cloze, questao, jurisprudencia)
```

---

## 4. Decisoes de Design e Justificativa

### 4.1 Protocol Pattern para LLM Client

**Decisao**: Usar `typing.Protocol` para definir a interface `LLMClient` em vez de uma classe abstrata (`ABC`).

**Justificativa**: Structural subtyping (duck typing estatico) — qualquer classe que implemente `generate_structured(system_prompt, user_message, response_model) -> T` satisfaz o protocolo sem heranca explicita. Isso simplifica testes (`MockLLMClient` nao precisa herdar nada) e permite troca de providers (OpenAI -> Anthropic -> modelo local) sem acoplamento. O `generator.py` depende apenas do protocolo, nao da implementacao.

### 4.2 Structured Outputs em vez de Parsing Manual

**Decisao**: Usar `client.beta.chat.completions.parse()` com `response_format=CardResponse` (modelo Pydantic) em vez de extrair JSON de texto livre.

**Justificativa**: O OpenAI Structured Outputs garante que a resposta do LLM obedece ao schema JSON derivado do modelo Pydantic. Isso elimina erros de parsing, campos ausentes e tipos incorretos — o output ja chega como instancia `CardResponse` validada. Sem isso, seria necessario regex/json.loads com tratamento de erros fragil.

### 4.3 Tenacity em vez de Retry do SDK

**Decisao**: Desabilitar retry interno do SDK OpenAI (`max_retries=0`) e usar Tenacity com configuracao explicita.

**Justificativa**: Controle fino sobre a estrategia de retry — backoff exponencial com jitter (`initial=1, max=30, jitter=2`), filtragem seletiva de excecoes (apenas `APIError`, `RateLimitError`, `APIConnectionError`), e logging de cada tentativa via `before_sleep`. O retry do SDK nao oferece esse nivel de visibilidade e customizacao.

### 4.4 Chunking por Paragrafos com Limite de 50k chars

**Decisao**: Dividir textos longos em chunks de ate 50k caracteres, quebrando em limites de paragrafo (`\n\n`).

**Justificativa**:
- 50k chars ≈ 12.5k tokens para portugues (~4 chars/token)
- Deixa margem para system prompt (~3k tokens) e resposta (~4k tokens) dentro do context window
- Quebra em paragrafos preserva contexto semantico (nao corta frases)
- Distribuicao proporcional de `max_cards` entre chunks garante cobertura uniforme
- Deduplicacao ao final evita cards repetidos entre chunks adjacentes

### 4.5 Singleton Settings no Import

**Decisao**: `settings = Settings()` instanciado no nivel de modulo em `config.py`.

**Justificativa**: Configuracao carregada uma unica vez no import, disponivel globalmente. Evita overhead de recarregar `.env` em cada operacao. Para testes, usar mocks (`monkeypatch`, `unittest.mock.patch`) em vez de tentar alterar o singleton — isso garante isolamento de testes sem efeitos colaterais.

### 4.6 Enums com StrEnum

**Decisao**: `CardType` e `Difficulty` herdam de `StrEnum`.

**Justificativa**: `StrEnum` permite comparacao direta com strings (`card.card_type == "basic"` funciona), serializacao automatica em JSON, e validacao de valores pelo Pydantic sem necessidade de custom validators. Elimina bugs de typo (valor invalido falha na construcao do enum).

### 4.7 Cache de Modelos Genanki

**Decisao**: `_model_cache` em `models.py` armazena modelos genanki ja criados, indexados por `card_type`.

**Justificativa**: Modelos genanki sao objetos pesados que registram templates, CSS e IDs. Recriar a cada card desperdicaria recursos e poderia gerar IDs inconsistentes (se `_generate_anki_id` fosse chamado novamente). O cache garante um unico modelo por tipo durante a vida do processo.

### 4.8 CSV com Separador `;`

**Decisao**: Usar ponto-e-virgula como separador no CSV default.

**Justificativa**: Padrao brasileiro para Excel, que usa `,` como separador decimal. Textos juridicos frequentemente contem virgulas, o que quebraria um CSV separado por `,` mesmo com quoting.

### 4.9 Validacao Separada do Prompt

**Decisao**: `validators.py` implementa regras de negocio independentes do prompt.

**Justificativa**: O prompt instrui o LLM, mas nao garante obediencia. A validacao pos-LLM funciona como "safety net" para rejeitar cards que nao atendem requisitos minimos (comprimento, campos obrigatorios, formato cloze). Prompt e validator devem estar sincronizados — se o prompt diz "OBRIGATORIO", o validator deve verificar.

### 4.10 Anti-Alucinacao como Bloco Fixo

**Decisao**: `ANTI_HALLUCINATION_INSTRUCTION` e sempre incluida no prompt, nunca condicionada a flags.

**Justificativa**: Em dominio juridico, referencias fabricadas (artigos inexistentes, sumulas inventadas) sao danosas e silenciosas — o usuario pode nao perceber o erro. A instrucao orienta o LLM a preferir omissao ("CF/88" generico) sobre fabricacao ("Art. 157-A" inexistente). Condicionar isso a um flag criaria risco de desabilitar por acidente.

### 4.11 Bullet Points no Prompt em vez de Numeracao

**Decisao**: Regras no prompt usam bullet points em vez de listas numeradas.

**Justificativa**: Blocos condicionais do prompt (ex: `legal_basis_instruction`) podem ser string vazia. Com numeracao fixa, a omissao de um bloco criaria gaps ("1, 2, 4, 5") que confundem o LLM. Bullet points evitam esse problema.

### 4.12 Lazy Import do OpenAI Client

**Decisao**: `OpenAILLMClient` e importado dentro de `generate_cards()` apenas quando `llm_client=None`.

**Justificativa**: Evita que `import openai` falhe quando o pacote nao esta instalado ou `OPENAI_API_KEY` nao esta configurada — util para testes que injetam `MockLLMClient`. O import acontece apenas no caminho que realmente precisa do client.

### 4.13 Injecao de Dependencia via Parametro

**Decisao**: `generate_cards()` aceita `llm_client` opcional.

**Justificativa**: Permite testes sem chamadas de API (injetando `MockLLMClient`), troca de provider em runtime, e controle fino sobre configuracao do client. Se nao fornecido, cria `OpenAILLMClient` com settings do singleton — zero-config para uso normal.

---

## 5. Restricoes e Limitacoes

### 5.1 Dependencias Externas

| Restricao | Impacto | Mitigacao |
|-----------|---------|-----------|
| Requer `OPENAI_API_KEY` valida | Sem API key, geracao falha | Validacao explicita em `generate_cards()` com mensagem clara |
| Dependente do modelo `gpt-4o-2024-08-06` | Model deprecation pode quebrar | Configuravel via `OPENAI_MODEL` em `.env` |
| AnkiConnect requer Anki Desktop rodando | Sincronizacao direta indisponivel se Anki fechado | AnkiConnect e opcional; exportacao APKG/CSV funciona standalone |
| PyMuPDF para PDFs (sem OCR) | PDFs escaneados (imagem) nao sao extraidos | `ParseError` explicito: "pode requerer OCR" |

### 5.2 Limites de Processamento

| Limite | Valor | Razao |
|--------|-------|-------|
| Max cards por chamada | 100 | Validacao em `generate_cards()` |
| Max chars por chunk | 50.000 | ~12.5k tokens, margem para prompt+resposta |
| Max clozes por card | 3 | Regra de validacao para evitar cards confusos |
| Min front length | 15 chars | Garantir pergunta minimamente informativa |
| Min back length | 20 chars | Garantir resposta minimamente completa |
| Max CLI cards | 1.000 | Validacao no argparser de `main.py` |

### 5.3 Limitacoes do LLM

- **Alucinacao**: Mesmo com `ANTI_HALLUCINATION_INSTRUCTION`, o LLM pode fabricar referencias legais. A mitigacao e instrucional, nao deterministica.
- **Qualidade variavel**: Cards gerados dependem da qualidade do texto de entrada e da capacidade do modelo. Textos muito curtos ou vagos produzem cards fracos.
- **Tipo automatico**: As heuristicas de selecao de tipo (`AUTO_TYPE_HEURISTICS`) sao orientacoes ao LLM, nao regras deterministicas. O LLM pode escolher tipos nao ideais.
- **Idioma fixo**: O prompt e os exemplos few-shot sao em portugues brasileiro para Direito Constitucional. Uso em outros idiomas ou areas juridicas requer adaptacao do prompt.

### 5.4 Limitacoes de Formato

- **basic_reversed**: Existe no enum `CardType` e no factory `_MODEL_FACTORY`, mas o LLM nao gera esse tipo — e usado apenas para importacao/exportacao manual.
- **CSV sanitiza newlines**: Quebras de linha no front/back sao substituidas por espacos. Formatacao rica do texto original e perdida no CSV/TSV.
- **APKG base64**: Util para APIs sem filesystem, mas o tamanho em base64 e ~33% maior que o binario original.
- **TSV simplificado**: Exporta apenas front, back e tags — nao inclui tipo nem extra.

### 5.5 Limitacoes Arquiteturais

- **Singleton settings**: Nao permite multiplas configuracoes simultaneas no mesmo processo. Cenarios multi-tenant precisariam de refatoracao para DI completa.
- **Processamento sincrono**: Chunks sao processados sequencialmente. Para textos muito longos com muitos chunks, nao ha paralelismo nas chamadas ao LLM.
- **Deduplicacao simples**: Baseada apenas no front (case-insensitive). Cards com frentes similares mas nao identicas nao sao detectados como duplicatas. Nao usa similaridade semantica.
- **Sem persistencia**: Nao ha banco de dados ou cache de cards gerados. Cada execucao e independente. Reprocessar o mesmo texto gera novos cards (possivelmente diferentes).
- **Sem versionamento de prompt**: Alteracoes no prompt nao sao rastreadas. Nao ha mecanismo para comparar qualidade entre versoes do prompt.

### 5.6 Hierarquia de Excecoes

```
Exception
├── ParseError              (parsers.py)    — erro na extracao de texto
├── CardGenerationError     (generator.py)  — erro na geracao via LLM
├── CardValidationError     (validators.py) — card invalido pos-LLM
│   attrs: .errors (list[str]), .card (AnkiCard | None)
├── ExportError             (exporters.py)  — erro na escrita de arquivo
└── AnkiConnectError        (anki_connect.py) — erro de comunicacao
```

Todas seguem o padrao `raise CustomError(...) from e` para preservar a cadeia de causas.
