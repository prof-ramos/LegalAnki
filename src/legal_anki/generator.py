"""Gerador de cards Anki via LLM usando OpenAI Structured Outputs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from .config import settings
from .prompts.system import build_system_prompt
from .utils import normalize_tags

if TYPE_CHECKING:
    from .llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class AnkiCard(BaseModel):
    """Modelo de um card Anki gerado."""

    front: str = Field(description="Texto da frente do card (pergunta ou cloze)")
    back: str = Field(description="Texto do verso do card (resposta)")
    card_type: Literal[
        "basic", "basic_reversed", "cloze", "questao", "jurisprudencia"
    ] = Field(description="Tipo do card")
    tags: list[str] = Field(description="Lista de tags para o card")
    extra: dict | None = Field(
        default=None,
        description="Campos adicionais dependendo do tipo (banca, ano, tribunal, fundamento, etc.)",
    )


class CardResponse(BaseModel):
    """Resposta estruturada do LLM com lista de cards."""

    cards: list[AnkiCard] = Field(description="Lista de cards gerados")


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

    Args:
        text: Texto fonte (artigo, súmula, questão, etc.)
        topic: Tópico principal (ex: "controle_concentrado", "direitos_fundamentais")
        difficulty: Nível de dificuldade ("facil", "medio", "dificil")
        include_legal_basis: Se True, instrui o LLM a sempre incluir fundamento legal
        card_type: Tipo de card a gerar ("auto" para deixar o LLM decidir)
        max_cards: Número máximo de cards a gerar
        llm_client: Cliente LLM opcional. Se None, usa OpenAI padrão com retry.

    Returns:
        Lista de AnkiCard gerados

    Raises:
        CardGenerationError: Se houver erro na geração
    """
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

    user_message = _build_user_message(text, topic, card_type, max_cards)

    logger.info(f"Gerando cards para tópico '{topic}'")

    try:
        result = llm_client.generate_structured(
            system_prompt=system_prompt,
            user_message=user_message,
            response_model=CardResponse,
        )

        if not result or not result.cards:
            raise CardGenerationError("LLM não retornou nenhum card")

        # Pós-processamento
        cards = _postprocess_cards(result.cards, topic, difficulty)

        logger.info(f"Gerados {len(cards)} cards com sucesso")
        return cards

    except CardGenerationError:
        raise
    except Exception as e:
        logger.error(f"Erro na geração de cards: {e}")
        raise CardGenerationError(f"Erro ao gerar cards: {e}") from e


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

        # Adiciona tag de dificuldade
        diff_tag = f"dificuldade_{difficulty}"
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
