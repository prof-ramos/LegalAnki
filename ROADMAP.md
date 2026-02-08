# 🗺️ Roadmap LegalAnki

Este documento descreve a visão de futuro do **LegalAnki** e os marcos planejados para transformar o estudo jurídico em uma experiência automatizada e de alta performance.

---

## 🚀 Fase 1: Estabilização e UX (v1.x)

_Foco: Robustez do sistema atual e facilidade de uso via CLI._

- [x] **Melhorias CSV:** Validação, sanitização e logging robusto.
- [x] **Interface CLI:** Execução via terminal com suporte a arquivos e texto.
- [ ] **Templates Premium:** Implementação de CSS moderno e responsivo para os modelos de cards no Anki.
- [ ] **Integração Anki-Connect:**
  - Auto-sincronização (`sync`) após exportação bem-sucedida.
  - Verificação de existência de decks e modelos antes da geração.
- [ ] **Documentação:** Guia completo de instalação e exemplos de uso em casos reais (Direito Administrativo, Penal, etc).

---

## 📦 Fase 2: Multimídia e Novos Formatos (v2.x)

_Foco: Expansão de funcionalidades e suporte nativo a arquivos Anki._

- [ ] **Exportação APKG Nativa:**
  - Suporte completo a modelos customizados sem dependência externa de importação.
  - Suporte a inclusão de mídia (imagens e áudio) via `genanki.Package.media_files`.
- [ ] **Novos Tipos de Cards:**
  - `Cloze` (Omissão de Palavras) para memorização de textos de lei seca.
  - Cards de "Vem na Prova" com estatísticas de incidência (extraídas via LLM).
- [ ] **Parsing Inteligente:**
  - Extração de texto diretamente de PDFs de julgados (Informativos STF/STJ) e Leis.
  - Limpeza de "ruído" jurídico (cabeçalhos, rodapés) antes da geração.

---

## 🌐 Fase 3: Ecossistema e Interface (v3.x)

_Foco: Escala, colaboração e facilidade multiplataforma._

- [ ] **Web Review UI:** Interface simples (Streamlit/Vite) para revisar, editar e deletar cards gerados pela IA antes de exportar.
- [ ] **LegalAnki Bot:** Integração com Telegram/Discord para enviar um trecho de lei e receber o arquivo CSV/APKG de volta.
- [ ] **Loja de Prompts Sociais:** Possibilidade de escolher "estilos" de outros usuários (Ex: Prompts focados em Magistratura vs. Delegado).
- [ ] **API Pública:** Wrapper para permitir que outros sites de cursos jurídicos integrem o botão "Gerar Cards" em seus materiais.

---

## ✅ Concluído

- Estrutura base do projeto (PoC).
- Abstração de LLM (OpenAI/Protocol).
- Validação robusta de Pydantic.
- Exportador CSV v1 sanitizado.
- CLI v1 funcional.

---

> [!TIP]
> Sugestões e contribuições são bem-vindas! Abra uma issue para discutirmos novas funcionalidades.
