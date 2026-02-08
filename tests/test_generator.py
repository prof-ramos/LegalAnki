"""Testes para funções auxiliares do generator."""

from legal_anki.generator import _chunk_text, _deduplicate_cards
from legal_anki.models import AnkiCard


class TestChunkText:
    """Testes para _chunk_text."""

    def test_short_text_single_chunk(self):
        """Texto curto retorna chunk único."""
        text = "Texto curto sobre direito constitucional."
        chunks = _chunk_text(text, max_chars=1000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_on_paragraphs(self):
        """Texto longo é dividido em limites de parágrafo."""
        para1 = "A" * 500
        para2 = "B" * 500
        para3 = "C" * 500
        text = f"{para1}\n\n{para2}\n\n{para3}"

        chunks = _chunk_text(text, max_chars=600)

        assert len(chunks) >= 2
        # Cada chunk deve conter pelo menos um parágrafo
        for chunk in chunks:
            assert len(chunk) > 0

    def test_preserves_all_content(self):
        """Todo o conteúdo original está presente nos chunks."""
        paragraphs = [f"Parágrafo {i} com conteúdo jurídico." for i in range(20)]
        text = "\n\n".join(paragraphs)

        chunks = _chunk_text(text, max_chars=200)

        reconstructed = "\n\n".join(chunks)
        assert reconstructed == text

    def test_single_huge_paragraph(self):
        """Parágrafo único maior que max_chars fica em chunk próprio."""
        text = "X" * 2000
        chunks = _chunk_text(text, max_chars=500)

        # Sem \n\n para dividir, cai em chunk único mesmo excedendo
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        """Texto vazio retorna chunk único vazio."""
        chunks = _chunk_text("", max_chars=100)
        assert len(chunks) == 1


class TestDeduplicateCards:
    """Testes para _deduplicate_cards."""

    def test_no_duplicates(self):
        """Sem duplicatas retorna todos os cards."""
        cards = [
            AnkiCard(front="Pergunta 1?", back="Resposta 1.", card_type="basic", tags=["t"]),
            AnkiCard(front="Pergunta 2?", back="Resposta 2.", card_type="basic", tags=["t"]),
        ]

        result = _deduplicate_cards(cards)
        assert len(result) == 2

    def test_removes_exact_duplicates(self):
        """Remove cards com front idêntico."""
        cards = [
            AnkiCard(front="Pergunta 1?", back="Resposta A.", card_type="basic", tags=["t"]),
            AnkiCard(front="Pergunta 1?", back="Resposta B.", card_type="basic", tags=["t"]),
        ]

        result = _deduplicate_cards(cards)
        assert len(result) == 1
        assert result[0].back == "Resposta A."  # Mantém o primeiro

    def test_case_insensitive(self):
        """Deduplicação é case-insensitive."""
        cards = [
            AnkiCard(front="Pergunta?", back="Resposta.", card_type="basic", tags=["t"]),
            AnkiCard(front="pergunta?", back="Outra.", card_type="basic", tags=["t"]),
        ]

        result = _deduplicate_cards(cards)
        assert len(result) == 1

    def test_empty_list(self):
        """Lista vazia retorna lista vazia."""
        assert _deduplicate_cards([]) == []
