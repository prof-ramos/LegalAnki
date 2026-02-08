# CLAUDE.md - Guia para Agentes IA no LegalAnki

Este arquivo orienta agentes de IA (Claude Code, Copilot, Cursor, etc.) sobre como trabalhar neste projeto.

## Sobre o Projeto

LegalAnki gera flashcards Anki de alta qualidade para Direito Constitucional usando LLMs (GPT-4o com Structured Outputs). Recebe texto juridico e devolve cards atomizados com fundamento legal, exportaveis em CSV, TSV, JSON e APKG.

## Comandos Essenciais

```bash
# Dependencias (usa uv, NAO pip)
uv sync

# Testes
uv run pytest tests/ -v
uv run pytest tests/ --cov=src    # com cobertura

# Linting e formatacao
ruff check src/ tests/
ruff format src/ tests/

# Executar CLI
uv run python main.py "texto juridico" --topic direitos_fundamentais
```

## Estrutura do Projeto

```
src/legal_anki/
  prompts/system.py    # System prompt e few-shot examples (ponto central de qualidade)
  generator.py         # Orquestra geracao: prompt -> LLM -> pos-processamento
  validators.py        # Validacao de negocio pos-LLM
  models.py            # Pydantic models (AnkiCard, CardResponse) + templates Anki
  exporters.py         # Export CSV, TSV, JSON, APKG
  serializers.py       # Mapeamento card -> campos Anki
  anki_connect.py      # Integracao com Anki Desktop (porta 8765)
  config.py            # Settings via pydantic-settings + .env
  utils.py             # Helpers (normalize_tags, escape_html, etc.)
  llm/
    protocol.py        # Interface LLMClient (Protocol)
    openai_client.py   # Implementacao OpenAI com retry (Tenacity)
tests/
  conftest.py          # Fixtures: sample_cards, sample_card_basic, sample_card_invalid
  test_validators.py   # Testes de validacao
  test_llm_client.py   # Testes do client LLM (com MockLLMClient)
  test_exporters.py    # Testes de exportacao
  test_utils.py        # Testes de utilidades
```

## Convencoes de Codigo

- **Python 3.13+** com `from __future__ import annotations`
- **Idioma**: comentarios, docstrings e logs em portugues brasileiro (PT-BR); nomes de funcoes/classes em ingles
- **Docstrings**: estilo Google
- **Linter**: Ruff (defaults)
- **Tipos**: usar type hints em todas as funcoes publicas
- **Imports condicionais**: usar `TYPE_CHECKING` para imports usados apenas em anotacoes
- **Excecoes**: criar excecoes customizadas (`CardGenerationError`, `CardValidationError`) e usar `raise ... from e`
- **Logging**: `logger = logging.getLogger(__name__)`, mensagens em PT-BR

## Arquitetura de Prompts

O system prompt em `prompts/system.py` e o ponto mais critico para qualidade dos cards.

**Regras ao modificar prompts:**
- `ANTI_HALLUCINATION_INSTRUCTION` deve estar sempre ativa (nunca condicionar a flags)
- `build_system_prompt()` usa keyword-only args e valida `difficulty` contra `_VALID_DIFFICULTIES`
- `EXAMPLE_CARDS` tem 4 exemplos few-shot (um por tipo) e sao injetados no prompt via `_format_examples()`
- Regras de conteudo usam bullet points (nunca numeracao fixa, para evitar gaps condicionais)
- O prompt e formatado com `str.format()` — usar `{{ }}` para chaves literais JSON

**Tipos de card e campos obrigatorios:**

| Tipo             | Campos `extra` obrigatorios          |
| ---------------- | ------------------------------------ |
| `basic`          | `fundamento` (opcional)              |
| `cloze`          | `fundamento` (opcional), max 3 clozes|
| `questao`        | `banca`, `ano`                       |
| `jurisprudencia` | `tribunal`, `tema`                   |

## Validacao

`validators.py` DEVE estar alinhado com o que o prompt exige:
- Se o prompt diz "OBRIGATORIO", o validator deve verificar
- Se o prompt diz "maximo de N", o validator deve rejeitar acima de N
- Verificar alinhamento ao alterar qualquer um dos dois arquivos

## Testes

- Usar `MockLLMClient` de `test_llm_client.py` para testar geracao sem API
- Fixtures em `conftest.py`: `sample_cards` (4 cards validos), `sample_card_basic`, `sample_card_invalid`
- Tag de dificuldade usa formato hierarquico: `dificuldade::medio` (com `::`, nao `_`)
- Os testes de `test_exporters.py` tem falhas pre-existentes (f-string com backslash, incompativel com Python < 3.12)

## Variaveis de Ambiente

Unica obrigatoria: `OPENAI_API_KEY`. Ver `.env.example` para todas as opcoes. Configuradas via `pydantic-settings` em `config.py`.

## Pontos de Atencao

- **Alucinacao legal**: o LLM pode inventar artigos/sumulas inexistentes. O prompt mitiga isso, mas a corretude depende de revisao humana
- **Structured Outputs**: usa `client.beta.chat.completions.parse()` com modelo Pydantic — garante JSON valido, mas nao garante conteudo correto
- **Temperature**: configuravel no `OpenAILLMClient` (default 0.7)
- **Retry**: Tenacity com backoff exponencial para APIError, RateLimitError, APIConnectionError
