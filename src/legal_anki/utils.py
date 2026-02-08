"""Utilitários para normalização e funções auxiliares."""

import re
import unicodedata


def slugify_tag(tag: str) -> str:
    """
    Normaliza tag para formato Anki-friendly.

    Remove acentos, substitui espaços por underscores e remove caracteres especiais.
    Preserva o separador hierárquico ``::`` do Anki.

    Args:
        tag: Tag original a ser normalizada

    Returns:
        Tag normalizada em lowercase sem acentos ou espaços
    """
    if not tag:
        return ""

    # Preserva separador hierárquico :: tratando cada segmento isoladamente
    parts = tag.split("::")
    slugified = [_slugify_segment(p) for p in parts]
    return "::".join(p for p in slugified if p)


def _slugify_segment(segment: str) -> str:
    """Normaliza um segmento individual de tag (sem ::)."""
    if not segment:
        return ""

    # Remove acentos
    segment = unicodedata.normalize("NFKD", segment)
    segment = segment.encode("ascii", "ignore").decode("ascii")

    # Substitui espaços por underscores
    segment = re.sub(r"\s+", "_", segment.strip())

    # Remove caracteres especiais (mantém letras, números, underscore e hífen)
    segment = re.sub(r"[^\w\-]", "", segment)

    return segment.lower()


def normalize_tags(tags: list[str]) -> list[str]:
    """
    Normaliza lista de tags.

    Args:
        tags: Lista de tags originais

    Returns:
        Lista de tags normalizadas, sem duplicatas e sem vazios
    """
    normalized = [slugify_tag(t) for t in tags if t]
    # Remove duplicatas mantendo ordem
    seen = set()
    unique = []
    for tag in normalized:
        if tag and tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique


def escape_html(text: str) -> str:
    """
    Escapa caracteres HTML especiais.

    Args:
        text: Texto a ser escapado

    Returns:
        Texto com caracteres HTML escapados
    """
    if not text:
        return ""
    replacements = [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ('"', "&quot;"),
        ("'", "&#x27;"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Trunca texto para um comprimento máximo.

    Args:
        text: Texto a ser truncado
        max_length: Comprimento máximo
        suffix: Sufixo a adicionar se truncado

    Returns:
        Texto truncado com sufixo se necessário
    """
    if not text or len(text) <= max_length:
        return text or ""
    return text[: max_length - len(suffix)].rstrip() + suffix
