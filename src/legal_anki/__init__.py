"""LegalAnki - Skill de Geração de Cards Anki para Direito Constitucional."""

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("legal-anki")
except Exception:
    __version__ = "0.1.0"
