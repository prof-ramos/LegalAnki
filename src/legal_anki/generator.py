"""Gerador de cards Anki via LLM usando OpenAI Structured Outputs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import settings
from .models import AnkiCard, CardResponse
from .prompts.system import build_system_prompt
from .utils import normalize_tags

if TYPE_CHECKING:
    from .llm.protocol import LLMClient

logger = logging.getLogger(__name__)

# Limite conservador para texto por chamada ao LLM.
# ~12 500 tokens para português (~4 chars/token), deixando margem para
# system prompt (~3k tokens) e resposta (~4k tokens) dentro do context window.
_MAX_CHUNK_CHARS = 50_000


class CardGenerationError(Exception):
    """Erro na geração de cards."""

    pass


def generate_cards(
    text: str,
    topic: str,
    difficulty: str = "medio",
    include_legal_basis: bool = True,
    card_type: str = "auto",
    max_cards: int = 10,
    llm_client: "LLMClient | None" = None,
) -> list[AnkiCard]:
    """
    Gera cards Anki a partir de um texto jurídico.

    Textos longos são automaticamente divididos em chunks e processados
    separadamente, com deduplicação ao final.

    Args:
        text: Texto fonte (artigo, súmula, questão, etc.)
        topic: Tópico principal (ex: "controle_concentrado", "direitos_fundamentais")
        difficulty: Nível de dificuldade ("facil", "medio", "dificil")
        include_legal_basis: Se True, instrui o LLM a sempre incluir fundamento legal
        card_type: Tipo de card a gerar ("auto" para deixar o LLM decidir)
        max_cards: Número máximo de cards a gerar (1-100)
        llm_client: Cliente LLM opcional. Se None, usa OpenAI padrão com retry.

    Returns:
        Lista de AnkiCard gerados

    Raises:
        ValueError: Se os parâmetros de entrada forem inválidos
        CardGenerationError: Se houver erro na geração
    """
    # Validação de inputs
    if not text or not text.strip():
        raise ValueError("Parâmetro 'text' não pode ser vazio")
    if not topic or not topic.strip():
        raise ValueError("Parâmetro 'topic' não pode ser vazio")
    if max_cards < 1 or max_cards > 100:
        raise ValueError("Parâmetro 'max_cards' deve estar entre 1 e 100")

    text = text.strip()
    topic = topic.strip()

    if llm_client is None:
        if not settings.openai_api_key:
            raise CardGenerationError(
                "OPENAI_API_KEY não configurada. Configure em .env ou variável de ambiente."
            )

        from .llm.openai_client import OpenAILLMClient

        llm_client = OpenAILLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    system_prompt = build_system_prompt(
        include_legal_basis=include_legal_basis,
        difficulty=difficulty,
    )

    logger.info("Gerando cards para tópico '%s'", topic)

    chunks = _chunk_text(text)

    if len(chunks) == 1:
        raw_cards = _call_llm(
            llm_client, system_prompt, chunks[0], topic, card_type, max_cards
        )
    else:
        logger.info("Texto dividido em %d partes para processamento", len(chunks))
        raw_cards = []
        cards_per_chunk = max(1, max_cards // len(chunks))
        remainder = max_cards % len(chunks)

        for i, chunk in enumerate(chunks):
            n = cards_per_chunk + (1 if i < remainder else 0)
            chunk_cards = _call_llm(
                llm_client, system_prompt, chunk, topic, card_type, n
            )
            raw_cards.extend(chunk_cards)

    if not raw_cards:
        raise CardGenerationError("LLM não retornou nenhum card")

    cards = _postprocess_cards(raw_cards, topic, difficulty)
    cards = _deduplicate_cards(cards)

    logger.info("Gerados %d cards com sucesso", len(cards))
    return cards[:max_cards]


def _call_llm(
    llm_client: "LLMClient",
    system_prompt: str,
    text: str,
    topic: str,
    card_type: str,
    max_cards: int,
) -> list[AnkiCard]:
    """Chama o LLM para um trecho de texto e retorna os cards crus."""
    user_message = _build_user_message(text, topic, card_type, max_cards)

    try:
        result = llm_client.generate_structured(
            system_prompt=system_prompt,
            user_message=user_message,
            response_model=CardResponse,
        )
        if not result or not result.cards:
            return []
        return result.cards
    except Exception as e:
        logger.warning("Erro ao processar chunk: %s", e)
        return []


def _build_user_message(text: str, topic: str, card_type: str, max_cards: int) -> str:
    """Constrói a mensagem do usuário para o LLM."""
    type_instruction = ""
    if card_type != "auto":
        type_instruction = f"\n\nGere apenas cards do tipo '{card_type}'."

    return f"""Gere até {max_cards} flashcards Anki sobre o seguinte conteúdo:

**Tópico**: {topic}

---
{text}
---

{type_instruction}

Retorne os cards em formato JSON conforme especificado."""


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """
    Divide texto longo em chunks menores respeitando limites de parágrafos.

    Args:
        text: Texto a dividir
        max_chars: Tamanho máximo de cada chunk em caracteres

    Returns:
        Lista de chunks (pelo menos 1)
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 2  # +2 para o \n\n separador

        if current_len + para_len > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_len = 0

        current_parts.append(para)
        current_len += para_len

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def _deduplicate_cards(cards: list[AnkiCard]) -> list[AnkiCard]:
    """Remove cards com front idêntico (case-insensitive), mantendo o primeiro."""
    seen: set[str] = set()
    unique: list[AnkiCard] = []

    for card in cards:
        key = card.front.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(card)

    return unique


def _postprocess_cards(
    cards: list[AnkiCard], topic: str, difficulty: str
) -> list[AnkiCard]:
    """
    Pós-processa os cards gerados.

    - Normaliza tags
    - Adiciona tag de tópico e dificuldade
    - Limpa espaços extras
    """
    processed = []

    for card in cards:
        # Normaliza tags existentes
        tags = normalize_tags(card.tags)

        # Adiciona tag de tópico se não existir
        topic_tag = normalize_tags([topic])[0] if topic else None
        if topic_tag and topic_tag not in tags:
            tags.insert(0, topic_tag)

        # Adiciona tag de dificuldade (formato hierárquico do Anki)
        diff_tag = f"dificuldade::{difficulty}"
        if diff_tag not in tags:
            tags.append(diff_tag)

        # Cria novo card com tags normalizadas
        processed_card = AnkiCard(
            front=card.front.strip(),
            back=card.back.strip(),
            card_type=card.card_type,
            tags=tags,
            extra=card.extra,
        )
        processed.append(processed_card)

    return processed
