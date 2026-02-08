# CLAUDE.md

Gerador de flashcards Anki para Direito Constitucional via LLM (GPT-4o Structured Outputs).
Stack: Python 3.13+, Pydantic, OpenAI, genanki, Tenacity. Gerenciamento de deps com `uv`.

## Comandos

```bash
uv sync                              # instalar dependencias (NUNCA usar pip)
uv run pytest tests/ -v              # rodar testes
uv run pytest tests/ --cov=src       # testes com cobertura
ruff check src/ tests/               # lint
ruff format src/ tests/              # formatar
uv run python main.py "texto" --topic direitos_fundamentais  # CLI
```

## Estilo

- Comentarios, docstrings e logs em portugues brasileiro; nomes de funcoes/classes em ingles
- Google-style docstrings
- `from __future__ import annotations` em todos os modulos
- Type hints em funcoes publicas; `TYPE_CHECKING` para imports de anotacao
- Excecoes customizadas com `raise ... from e`
- Logging: `logger = logging.getLogger(__name__)`

## Arquitetura

```
src/legal_anki/
  prompts/system.py  -> system prompt + few-shot (ponto critico de qualidade)
  generator.py       -> orquestra: prompt -> LLM -> pos-processamento
  validators.py      -> validacao de negocio pos-LLM
  models.py          -> AnkiCard, CardResponse (Pydantic) + templates genanki
  llm/protocol.py    -> interface LLMClient (Protocol)
  llm/openai_client.py -> implementacao OpenAI + retry (Tenacity)
  exporters.py       -> CSV, TSV, JSON, APKG
  config.py          -> Settings via pydantic-settings + .env
```

## Gotchas

- **Prompt <-> Validator devem estar sincronizados**: se o prompt diz "OBRIGATORIO", `validators.py` deve verificar. Sempre checar alinhamento ao alterar qualquer um dos dois.
- **`ANTI_HALLUCINATION_INSTRUCTION`** deve estar sempre ativa — nunca condicionar a flags.
- **Regras no prompt usam bullet points**, nunca numeracao fixa (evita gaps quando blocos condicionais sao omitidos).
- **`{{ }}`** no prompt: o template usa `str.format()`, entao chaves literais JSON precisam de escape duplo.
- **Tag de dificuldade** usa formato hierarquico Anki: `dificuldade::medio` (com `::`, nao `_`).
- **`test_exporters.py`** tem falhas pre-existentes (f-string com backslash, incompativel com Python < 3.12).
- **Unica variavel obrigatoria**: `OPENAI_API_KEY`. Ver `.env.example` para as demais.

## Tipos de Card

| Tipo             | Campos `extra` obrigatorios | Validacao                  |
| ---------------- | --------------------------- | -------------------------- |
| `basic`          | `fundamento` (opcional)     | front min 15, back min 20  |
| `basic_reversed` | `fundamento` (opcional)     | front min 15, back min 20  |
| `cloze`          | `fundamento` (opcional)     | requer `{{cN::}}`, max 3   |
| `questao`        | `banca`, `ano`              | ambos obrigatorios         |
| `jurisprudencia` | `tribunal`, `tema`          | ambos obrigatorios         |

## Testes

- Usar `MockLLMClient` (em `test_llm_client.py`) para testar geracao sem chamar API real
- Fixtures em `conftest.py`: `sample_cards` (4 validos), `sample_card_basic`, `sample_card_invalid`
- `build_system_prompt()` usa keyword-only args e valida `difficulty` contra `_VALID_DIFFICULTIES`
