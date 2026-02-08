"""Exportadores para múltiplos formatos (CSV, TSV, JSON, APKG)."""

from __future__ import annotations

import base64
import csv
import json
import logging
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import genanki

from .config import settings
from .models import get_model_for_card_type
from .serializers import map_card_to_fields

if TYPE_CHECKING:
    from .models import AnkiCard

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Erro durante exportação."""

    pass


# =============================================================================
# CSV Export (DEFAULT)
# =============================================================================


def _sanitize_text(text: str | None, separator_char: str = ";") -> str:
    """Remove quebras de linha e caracteres problemáticos para CSV/TSV."""
    if not text:
        return ""
    # Remove tabs (se for o separador), newlines e carriage returns
    return (
        text.replace("\n", " ").replace("\r", "").replace(separator_char, " ").strip()
    )


def export_to_csv(
    cards: list["AnkiCard"],
    output_path: Path | str | None = None,
    include_header: bool = True,
) -> str | Path:
    """
    Exporta cards para CSV (formato default V1).

    Usa ponto-e-vírgula como separador para compatibilidade com Excel BR.
    Sanitiza quebras de linha para evitar corrupção do CSV.

    Args:
        cards: Lista não-vazia de cards a exportar
        output_path: Caminho do arquivo de saída. Se None, retorna string.
        include_header: Se True, inclui cabeçalho

    Returns:
        Path do arquivo criado ou string com o conteúdo CSV

    Raises:
        ExportError: Se a lista de cards estiver vazia
    """
    if not cards:
        raise ExportError("Lista de cards vazia para exportação CSV")

    if not output_path:
        output_path = None

    output = StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)

    if include_header:
        writer.writerow(["front", "back", "tags", "type", "extra"])

    for card in cards:
        tags_str = _sanitize_text(" ".join(card.tags))
        extra_str = (
            _sanitize_text(json.dumps(card.extra, ensure_ascii=False))
            if card.extra
            else ""
        )
        writer.writerow(
            [
                _sanitize_text(card.front, separator_char=";"),
                _sanitize_text(card.back, separator_char=";"),
                tags_str,
                card.card_type,
                extra_str,
            ]
        )

    csv_content = output.getvalue()

    if output_path is None:
        logger.info("Exportados %d cards para CSV (string)", len(cards))
        return csv_content

    output_path = Path(output_path) if output_path else Path("legal_anki_cards.csv")
    try:
        output_path.write_text(csv_content, encoding="utf-8")
        logger.info("Exportados %d cards para CSV: %s", len(cards), output_path)
    except Exception as e:
        raise ExportError(
            f"Erro ao escrever arquivo CSV para {output_path}: {e}"
        ) from e
    return output_path


# =============================================================================
# TSV Export
# =============================================================================


def export_to_tsv(
    cards: list["AnkiCard"],
    output_path: Path | str | None = None,
) -> str | Path:
    """
    Exporta cards para TSV (Tab-Separated Values).

    Formato simples compatível com importação direta no Anki.

    Args:
        cards: Lista de cards a exportar
        output_path: Caminho do arquivo de saída. Se None, usa um nome padrão.

    Returns:
        Path do arquivo criado ou string com o conteúdo TSV

    Raises:
        ExportError: Se a lista de cards estiver vazia
    """
    if not cards:
        raise ExportError("Lista de cards vazia para exportação TSV")

    if not output_path:
        output_path = (
            None  # Garantir que se for string vazia vire None para o check abaixo
        )

    lines = []

    tab = "\t"
    for card in cards:
        tags_str = _sanitize_text(" ".join(card.tags))
        # TSV simples: front\tback\ttags
        front = _sanitize_text(card.front, separator_char=tab)
        back = _sanitize_text(card.back, separator_char=tab)
        line = f"{front}\t{back}\t{tags_str}"
        lines.append(line)

    tsv_content = "\n".join(lines)

    if output_path is None:
        logger.info("Exportados %d cards para TSV (string)", len(cards))
        return tsv_content

    output_path = Path(output_path)
    try:
        output_path.write_text(tsv_content, encoding="utf-8")
        logger.info("Exportados %d cards para TSV: %s", len(cards), output_path)
    except Exception as e:
        raise ExportError(
            f"Erro ao escrever arquivo TSV para {output_path}: {e}"
        ) from e
    return output_path


# =============================================================================
# JSON Export
# =============================================================================


def export_to_json(
    cards: list["AnkiCard"],
    output_path: Path | str | None = None,
    include_metadata: bool = True,
) -> str | Path:
    """
    Exporta cards para JSON com metadata opcional.

    Args:
        cards: Lista de cards a exportar
        output_path: Caminho do arquivo de saída. Se None, usa um nome padrão.
        include_metadata: Se True, inclui metadata (versão, modelo, timestamp)

    Returns:
        Path do arquivo criado ou string com o conteúdo JSON

    Raises:
        ExportError: Se a lista de cards estiver vazia
    """
    if not cards:
        raise ExportError("Lista de cards vazia para exportação JSON")

    if not output_path:
        output_path = None

    data: dict = {}

    if include_metadata:
        data["metadata"] = {
            "skill_version": settings.skill_version,
            "model": settings.openai_model,
            "generated_at": datetime.now().isoformat(),
            "total_cards": len(cards),
        }

    data["cards"] = [card.model_dump() for card in cards]

    json_content = json.dumps(data, ensure_ascii=False, indent=2)

    if output_path is None:
        logger.info("Exportados %d cards para JSON (string)", len(cards))
        return json_content

    output_path = Path(output_path)
    try:
        output_path.write_text(json_content, encoding="utf-8")
        logger.info("Exportados %d cards para JSON: %s", len(cards), output_path)
    except Exception as e:
        raise ExportError(
            f"Erro ao escrever arquivo JSON para {output_path}: {e}"
        ) from e
    return output_path


# =============================================================================
# APKG Export
# =============================================================================


def export_to_apkg(
    cards: list["AnkiCard"],
    deck_name: str = "LegalAnki",
    output_path: Path | str | None = None,
) -> Path:
    """
    Exporta cards para arquivo .apkg (Anki Package).

    Args:
        cards: Lista de cards a exportar
        deck_name: Nome do deck no Anki
        output_path: Caminho do arquivo .apkg. Se None, usa um nome padrão.

    Returns:
        Path do arquivo criado

    Raises:
        ExportError: Se a lista de cards estiver vazia
    """
    if not cards:
        raise ExportError("Lista de cards vazia para exportação APKG")

    output_path = Path(output_path or "legal_anki_deck.apkg")

    deck = genanki.Deck(
        deck_id=settings.anki_deck_id,
        name=deck_name,
    )

    for card in cards:
        model = get_model_for_card_type(card.card_type)
        fields = map_card_to_fields(card)

        note = genanki.Note(
            model=model,
            fields=fields,
            tags=card.tags,
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    try:
        package.write_to_file(str(output_path))
        logger.info("Exportados %d cards para APKG: %s", len(cards), output_path)
    except Exception as e:
        raise ExportError(
            f"Erro ao escrever arquivo APKG para {output_path}: {e}"
        ) from e
    return output_path


def export_to_apkg_base64(
    cards: list["AnkiCard"],
    deck_name: str,
) -> str:
    """
    Exporta cards para APKG em formato base64 usando BytesIO (sem tempfile).

    Útil para APIs e bots que precisam transmitir o arquivo.

    Args:
        cards: Lista de cards a exportar
        deck_name: Nome do deck no Anki

    Returns:
        String base64 do arquivo .apkg
    """
    deck = genanki.Deck(
        deck_id=settings.anki_deck_id,
        name=deck_name,
    )

    for card in cards:
        model = get_model_for_card_type(card.card_type)
        fields = map_card_to_fields(card)

        note = genanki.Note(
            model=model,
            fields=fields,
            tags=card.tags,
        )
        deck.add_note(note)

    package = genanki.Package(deck)

    # Usa BytesIO ao invés de tempfile
    buffer = BytesIO()
    package.write_to_file(buffer)
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


# =============================================================================
# Unified Export Function
# =============================================================================


def export_cards(
    cards: list["AnkiCard"],
    output_path: Path | str,
    format: str = "csv",
    deck_name: str = "LegalAnki",
    **kwargs,
) -> Path | str:
    """
    Função unificada de exportação.

    Args:
        cards: Lista de cards a exportar
        output_path: Caminho do arquivo de saída
        format: Formato de exportação ("csv", "tsv", "json", "apkg")
        deck_name: Nome do deck (apenas para APKG)
        **kwargs: Argumentos adicionais para o exportador específico

    Returns:
        Path do arquivo criado
    """
    format = format.lower()

    if format == "csv":
        return export_to_csv(cards, output_path, **kwargs)
    elif format == "tsv":
        return export_to_tsv(cards, output_path)
    elif format == "json":
        return export_to_json(cards, output_path, **kwargs)
    elif format == "apkg":
        return export_to_apkg(cards, deck_name, output_path)
    else:
        raise ExportError(
            f"Formato não suportado: {format}. Use csv, tsv, json ou apkg."
        )
