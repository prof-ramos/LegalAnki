"""Testes para o módulo de validação."""

import pytest

from legal_anki.validators import (
    CardValidationError,
    validate_card,
    validate_cards_batch,
)


class TestValidateCard:
    """Testes para validate_card."""

    def test_valid_basic_card(self, sample_card_basic):
        """Card válido deve passar na validação."""
        assert validate_card(sample_card_basic) is True

    def test_invalid_card_short_front(self, sample_card_invalid):
        """Card com front curto deve falhar."""
        with pytest.raises(CardValidationError) as exc_info:
            validate_card(sample_card_invalid)

        assert "Front muito curto" in str(exc_info.value)

    def test_invalid_card_empty_back(self, sample_card_invalid):
        """Card com back vazio deve falhar."""
        with pytest.raises(CardValidationError) as exc_info:
            validate_card(sample_card_invalid)

        assert "Back muito curto" in str(exc_info.value)

    def test_invalid_card_no_tags(self, sample_card_invalid):
        """Card sem tags deve falhar."""
        with pytest.raises(CardValidationError) as exc_info:
            validate_card(sample_card_invalid)

        assert "sem tags" in str(exc_info.value)

    def test_valid_card_without_legal_basis_requirement(self):
        """Card sem fundamento legal é válido se não exigido."""
        from legal_anki.generator import AnkiCard

        card = AnkiCard(
            front="Qual é a capital do Brasil?",
            back="Brasília é a capital federal.",
            card_type="basic",
            tags=["geografia"],
            extra=None,
        )

        # Sem exigir fundamento legal
        assert validate_card(card, require_legal_basis=False) is True

    def test_invalid_card_missing_legal_basis(self):
        """Card sem fundamento legal falha se exigido."""
        from legal_anki.generator import AnkiCard

        card = AnkiCard(
            front="Qual é a capital do Brasil?",
            back="Brasília é a capital federal.",
            card_type="basic",
            tags=["geografia"],
            extra=None,
        )

        with pytest.raises(CardValidationError) as exc_info:
            validate_card(card, require_legal_basis=True)

        assert "fundamento legal" in str(exc_info.value)

    def test_valid_card_with_legal_basis_in_back(self):
        """Card com fundamento legal no back é válido."""
        from legal_anki.generator import AnkiCard

        card = AnkiCard(
            front="Qual é o fundamento do habeas corpus?",
            back="O habeas corpus está previsto no Art. 5º, LXVIII, da CF/88.",
            card_type="basic",
            tags=["garantias"],
            extra=None,
        )

        assert validate_card(card, require_legal_basis=True) is True

    def test_cloze_without_deletion_fails(self):
        """Card cloze sem marcação de lacuna deve falhar."""
        from legal_anki.generator import AnkiCard

        card = AnkiCard(
            front="O STF é composto por 11 ministros.",  # Sem {{c1::}}
            back="Composição do STF",
            card_type="cloze",
            tags=["stf"],
            extra={"fundamento": "Art. 101, CF"},
        )

        with pytest.raises(CardValidationError) as exc_info:
            validate_card(card)

        assert "cloze sem marcação" in str(exc_info.value)

    def test_questao_without_banca_fails(self):
        """Card questão sem banca deve falhar."""
        from legal_anki.generator import AnkiCard

        card = AnkiCard(
            front="O direito ao silêncio é absoluto?",
            back="Não, admite exceções.",
            card_type="questao",
            tags=["direitos"],
            extra={"fundamento": "Art. 5º, LXIII"},  # Sem banca
        )

        with pytest.raises(CardValidationError) as exc_info:
            validate_card(card)

        assert "sem banca" in str(exc_info.value)


class TestValidateCardsBatch:
    """Testes para validate_cards_batch."""

    def test_all_valid_cards(self, sample_cards):
        """Todos os cards válidos devem passar."""
        valid, errors = validate_cards_batch(sample_cards, skip_invalid=True)

        assert len(valid) == len(sample_cards)
        assert len(errors) == 0

    def test_skip_invalid_cards(self, sample_cards, sample_card_invalid):
        """Cards inválidos são pulados com skip_invalid=True."""
        cards = sample_cards + [sample_card_invalid]

        valid, errors = validate_cards_batch(cards, skip_invalid=True)

        assert len(valid) == len(sample_cards)
        assert len(errors) == 1

    def test_raise_on_invalid_card(self, sample_card_invalid):
        """Deve levantar exceção com skip_invalid=False."""
        with pytest.raises(CardValidationError):
            validate_cards_batch([sample_card_invalid], skip_invalid=False)
