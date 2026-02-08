# Guia do Desenvolvedor - LegalAnki ⚖️🧠

Este documento fornece informações técnicas detalhadas para desenvolvedores que desejam contribuir ou entender a arquitetura do LegalAnki.

## 1. Instruções de Configuração

O projeto utiliza o `uv` para gerenciamento de dependências e ambientes virtuais.

### Pré-requisitos

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) instalado
- Anki Desktop (se desejar testar a exportação direta via AnkiConnect)

### Configuração Passo a Passo

1. **Clone o repositório**:

   ```bash
   git clone https://github.com/gabrielramos/LegalAnki.git
   cd LegalAnki
   ```

2. **Sincronize as dependências**:

   ```bash
   uv sync
   ```

3. **Configure as variáveis de ambiente**:
   Crie um arquivo `.env` baseado no `.env.example`:

   ```bash
   cp .env.example .env
   ```

   _Obrigatório_: `OPENAI_API_KEY`.

4. **Instale o AnkiConnect (opcional)**:
   No Anki Desktop, vá em `Ferramentas -> Complementos -> Obter Complementos` e instale o código `2055179261`.

---

## 2. Visão Geral da Estrutura

```text
LegalAnki/
├── main.py              # Entry point do CLI
├── src/legal_anki/
│   ├── models.py        # Modelos Pydantic e lógica genanki
│   ├── generator.py     # Orquestrador de geração de cards
│   ├── exporters.py     # Lógica de exportação (CSV, TSV, JSON, APKG)
│   ├── anki_connect.py  # Integração com Anki Desktop API
│   ├── llm/             # Clientes de LLM (OpenAI)
│   ├── prompts/         # Templates de prompts do sistema
│   └── config.py        # Gerenciamento de configurações via pydantic-settings
└── tests/               # Suíte de testes (pytest)
```

### Arquitetura de Fluxo de Dados

1. **Input**: O usuário fornece um texto jurídico ou arquivo `.txt`.
2. **Geração**: O `generator.py` envia o texto para o `OpenAILLMClient` utilizando _Structured Outputs_ para garantir um JSON válido.
3. **Validação**: Os cards retornados são validados pelo modelo `AnkiCard` (Pydantic).
4. **Exportação**: O usuário escolhe o formato (CSV por padrão), processado em `exporters.py`.

---

## 3. Fluxo de Trabalho de Desenvolvimento

### Adicionando Novos Prompts

Os prompts estão centralizados em `src/legal_anki/prompts/system.py`. Para ajustar a qualidade da geração, edite os templates nesta pasta.

### Alterando Modelos de Cards

A lógica visual dos cards (HTML/CSS) está em `src/legal_anki/models.py`. Se você quiser mudar como o card aparece no Anki, altere o `CSS` e os `templates` nas classes de modelo.

### Estilo de Código

- Usamos **Ruff** para linting e formatação.
- Comentários e logs devem estar em **Português Brasileiro (PT-BR)**.

---

## 4. Abordagem de Teste

Utilizamos `pytest` para testes unitários e de integração.

### Como rodar os testes

```bash
uv run pytest tests/           # Todos os testes
uv run pytest --cov=src        # Com relatório de cobertura
```

### Mocking

Para evitar gastos com API durante os testes, utilizamos mocks para as chamadas do cliente OpenAI. Veja `tests/test_llm_client.py` para exemplos.

---

## 5. Solução de Problemas Comuns

### Erro de Conexão com AnkiConnect

- Verifique se o Anki Desktop está aberto.
- Certifique-se de que o complemento AnkiConnect está instalado.
- O padrão é `http://localhost:8765`.

### LLM Recusa Gerar Cards

- Isso geralmente acontece se o texto de entrada for muito curto ou não contiver conteúdo jurídico processável.
- Verifique o log: `logger.warning` mostrará a recusa do modelo.

### Caracteres Especiais no CSV

- Se os cards ficarem "quebrados" no Excel/Google Sheets, certifique-se de importar usando codificação **UTF-8**.
- Nossa exportação utiliza sanitização automática para evitar quebras de linha indesejadas dentro das células.
