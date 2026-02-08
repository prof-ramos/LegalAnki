"""Serializadores para conversão de cards Anki para diferentes formatos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import CardType

if TYPE_CHECKING:
    from .models import AnkiCard


def map_card_to_fields(card: "AnkiCard") -> list[str]:
    """
    Mapeia um AnkiCard para os campos do modelo Anki correspondente.

    Args:
        card: Card a ser mapeado

    Returns:
        Lista de valores de campos na ordem correta para o modelo
    """
    extra = card.extra or {}

    if card.card_type == CardType.CLOZE:
        return [
            card.front,  # Text (com marcações cloze)
            extra.get("fundamento", ""),  # Extra
        ]

    if card.card_type == CardType.QUESTAO:
        return [
            card.front,
            card.back,
            extra.get("banca", ""),
            extra.get("ano", ""),
            extra.get("cargo", ""),
            extra.get("fundamento", ""),
        ]

    if card.card_type == CardType.JURISPRUDENCIA:
        return [
            card.front,
            card.back,
            extra.get("tribunal", ""),
            extra.get("data_julgamento", ""),
            extra.get("tema", ""),
            extra.get("fundamento_legal", ""),
        ]

    # basic e basic_reversed
    return [card.front, card.back]
