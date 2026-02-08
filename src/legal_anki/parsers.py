"""Parsers para extração de texto de diferentes formatos de arquivo."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensões suportadas (sem ponto)
SUPPORTED_EXTENSIONS = {"txt", "pdf", "docx", "csv"}


class ParseError(Exception):
    """Erro ao extrair texto de um arquivo."""

    pass


def parse_file(path: Path) -> str:
    """
    Extrai texto de um arquivo baseado na extensão.

    Args:
        path: Caminho do arquivo de entrada

    Returns:
        Texto extraído do arquivo

    Raises:
        ParseError: Se o formato não for suportado ou houver erro na leitura
        FileNotFoundError: Se o arquivo não existir
    """
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    ext = path.suffix.lower().lstrip(".")

    if ext not in SUPPORTED_EXTENSIONS:
        raise ParseError(
            f"Formato não suportado: .{ext}. "
            f"Use: {', '.join(f'.{e}' for e in sorted(SUPPORTED_EXTENSIONS))}"
        )

    parser = _PARSERS[ext]
    try:
        text = parser(path)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Erro ao ler arquivo {path.name}: {e}") from e

    if not text or not text.strip():
        raise ParseError(f"Arquivo {path.name} está vazio ou não contém texto extraível")

    logger.info("Extraídos %d caracteres de %s", len(text.strip()), path.name)
    return text.strip()


def _parse_txt(path: Path) -> str:
    """Lê arquivo de texto puro."""
    return path.read_text(encoding="utf-8")


def _parse_pdf(path: Path) -> str:
    """Extrai texto de PDF usando PyMuPDF (sem OCR)."""
    import pymupdf

    pages = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)

    if not pages:
        raise ParseError(f"PDF {path.name} não contém texto extraível (pode requerer OCR)")

    return "\n\n".join(pages)


def _parse_docx(path: Path) -> str:
    """Extrai texto de DOCX usando python-docx."""
    import docx

    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_csv(path: Path) -> str:
    """
    Extrai texto de CSV concatenando todas as células.

    Trata o CSV como fonte de conteúdo jurídico tabular,
    concatenando cada linha como um bloco de texto.
    """
    raw = path.read_text(encoding="utf-8")

    # Detectar delimitador (;, , ou \t)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(raw[:2048])
    except csv.Error:
        dialect = csv.excel  # fallback para vírgula

    reader = csv.reader(StringIO(raw), dialect)
    rows = list(reader)

    if not rows:
        raise ParseError(f"CSV {path.name} está vazio")

    # Se a primeira linha parecer cabeçalho, pula
    header = rows[0]
    has_header = all(cell.strip().isidentifier() or cell.strip().replace(" ", "_").isidentifier() for cell in header if cell.strip())

    start = 1 if has_header and len(rows) > 1 else 0
    lines = []
    for row in rows[start:]:
        # Junta células não-vazias com " | "
        cells = [cell.strip() for cell in row if cell.strip()]
        if cells:
            lines.append(" | ".join(cells))

    return "\n".join(lines)


# Mapa de extensão -> função parser
_PARSERS = {
    "txt": _parse_txt,
    "pdf": _parse_pdf,
    "docx": _parse_docx,
    "csv": _parse_csv,
}
