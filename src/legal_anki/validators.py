"""Validadores para cards gerados pelo LLM."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .config import CardType

if TYPE_CHECKING:
    from .models import AnkiCard


class CardValidationError(Exception):
    """Erro de validação de card."""

    def __init__(self, errors: list[str], card: "AnkiCard | None" = None):
        self.errors = errors
        self.card = card
        super().__init__("; ".join(errors))


def validate_card(
    card: "AnkiCard",
    require_legal_basis: bool = True,
    min_front_length: int = 10,
    min_back_length: int = 5,
) -> bool:
    """
    Valida um card gerado pelo LLM.

    Args:
        card: Card a ser validado
        require_legal_basis: Se True, exige fundamento legal
        min_front_length: Comprimento mínimo do front
        min_back_length: Comprimento mínimo do back

    Returns:
        True se válido

    Raises:
        CardValidationError: Se o card for inválido
    """
    errors = []

    # Validação de campos obrigatórios básicos
    if not card.front or len(card.front.strip()) < min_front_length:
        errors.append(f"Front muito curto (mínimo {min_front_length} caracteres)")

    if not card.back or len(card.back.strip()) < min_back_length:
        errors.append(f"Back muito curto (mínimo {min_back_length} caracteres)")

    if not card.tags:
        errors.append("Card sem tags")

    # Validação do tipo de card usando Enum
    valid_types = [t.value for t in CardType]
    if card.card_type not in valid_types:
        errors.append(f"Tipo de card inválido: {card.card_type}")

    # Validação específica por tipo
    if card.card_type == CardType.CLOZE:
        if "{{c1::" not in card.front and "{{c2::" not in card.front:
            errors.append("Card cloze sem marcação de lacuna ({{c1::...}})")
        else:
            # Verifica máximo de 3 clozes por card
            cloze_count = len(re.findall(r"\{\{c\d+::", card.front))
            if cloze_count > 3:
                errors.append(
                    f"Card cloze com {cloze_count} lacunas (máximo 3)"
                )

    if card.card_type == CardType.QUESTAO:
        if not card.extra or not card.extra.get("banca"):
            errors.append("Questão sem banca definida")
        if not card.extra or not card.extra.get("ano"):
            errors.append("Questão sem ano definido")

    if card.card_type == CardType.JURISPRUDENCIA:
        if not card.extra or not card.extra.get("tribunal"):
            errors.append("Jurisprudência sem tribunal definido")
        if not card.extra or not card.extra.get("tema"):
            errors.append("Jurisprudência sem tema definido")

    # Validação de fundamento legal
    if require_legal_basis:
        has_fundamento = _check_legal_basis(card)
        if not has_fundamento:
            errors.append("Card sem fundamento legal (art., súmula, ADI, etc.)")

    if errors:
        raise CardValidationError(errors, card)

    return True


def _check_legal_basis(card: "AnkiCard") -> bool:
    """
    Verifica se o card contém fundamento legal.

    Procura em extra.fundamento, extra.fundamento_legal ou no próprio back.
    """
    # Verifica em extra
    if card.extra:
        fundamento = card.extra.get("fundamento") or card.extra.get("fundamento_legal")
        if fundamento and len(str(fundamento).strip()) > 3:
            return True

    # Verifica keywords no back
    keywords = [
        "art.",
        "artigo",
        "súmula",
        "sumula",
        "sv ",
        "adi",
        "adc",
        "adpf",
        "§",
        "inciso",
        "alínea",
        "cf/88",
        "cf/1988",
        "constituição federal",
        "re ",
        "resp",
        "hc ",
        "ms ",
    ]

    back_lower = card.back.lower() if card.back else ""
    return any(kw in back_lower for kw in keywords)


def validate_cards_batch(
    cards: list["AnkiCard"],
    require_legal_basis: bool = True,
    skip_invalid: bool = False,
) -> tuple[list["AnkiCard"], list[CardValidationError]]:
    """
    Valida uma lista de cards.

    Args:
        cards: Lista de cards a validar
        require_legal_basis: Se True, exige fundamento legal
        skip_invalid: Se True, retorna cards válidos e lista de erros;
                     Se False, levanta exceção no primeiro erro

    Returns:
        Tupla (cards_válidos, erros) se skip_invalid=True

    Raises:
        CardValidationError: Se skip_invalid=False e algum card for inválido
    """
    valid_cards = []
    errors = []

    for card in cards:
        try:
            validate_card(card, require_legal_basis=require_legal_basis)
            valid_cards.append(card)
        except CardValidationError as e:
            if skip_invalid:
                errors.append(e)
            else:
                raise

    return valid_cards, errors
