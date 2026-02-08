"""Configuração do pytest."""

import sys
from pathlib import Path

import pytest

# Adiciona src ao path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_cards():
    """Retorna cards de exemplo para testes."""
    from legal_anki.generator import AnkiCard

    return [
        AnkiCard(
            front="Qual é o fundamento constitucional do direito ao silêncio?",
            back="Art. 5º, LXIII, CF/88 - O preso tem direito de permanecer calado.",
            card_type="basic",
            tags=["direitos_fundamentais", "garantias_processuais"],
            extra={"fundamento": "Art. 5º, LXIII, CF/88"},
        ),
        AnkiCard(
            front="A Súmula Vinculante {{c1::11}} trata do uso de {{c2::algemas}}.",
            back="SV 11 - Uso de algemas",
            card_type="cloze",
            tags=["sumulas_vinculantes", "stf"],
            extra={"fundamento": "Art. 5º, III, X e XLIX, CF/88"},
        ),
        AnkiCard(
            front="(CESPE/2023) O direito ao silêncio é absoluto e não admite exceções.",
            back="ERRADO. O direito ao silêncio não é absoluto. Existem situações em que o acusado deve se identificar.",
            card_type="questao",
            tags=["direitos_fundamentais", "cespe"],
            extra={
                "banca": "CESPE",
                "ano": "2023",
                "cargo": "Juiz Federal",
                "fundamento": "Art. 5º, LXIII, CF/88",
            },
        ),
        AnkiCard(
            front="Qual o entendimento do STF sobre uso de algemas?",
            back="Só é lícito o uso de algemas em casos de resistência, fundado receio de fuga ou perigo.",
            card_type="jurisprudencia",
            tags=["stf", "sumulas_vinculantes"],
            extra={
                "tribunal": "STF",
                "tema": "Uso de algemas",
                "fundamento_legal": "Súmula Vinculante 11",
            },
        ),
    ]


@pytest.fixture
def sample_card_basic():
    """Retorna um card básico para testes."""
    from legal_anki.generator import AnkiCard

    return AnkiCard(
        front="Qual é o fundamento constitucional do direito ao silêncio?",
        back="Art. 5º, LXIII, CF/88 - O preso tem direito de permanecer calado.",
        card_type="basic",
        tags=["direitos_fundamentais"],
        extra={"fundamento": "Art. 5º, LXIII, CF/88"},
    )


@pytest.fixture
def sample_card_invalid():
    """Retorna um card inválido para testes."""
    from legal_anki.generator import AnkiCard

    return AnkiCard(
        front="X",  # Muito curto
        back="",  # Vazio
        card_type="basic",
        tags=[],  # Sem tags
        extra=None,
    )
