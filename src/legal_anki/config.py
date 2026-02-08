"""Configurações e constantes do LegalAnki."""

import random
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Carrega .env do diretório raiz do projeto
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")


def _generate_anki_id() -> int:
    """Gera um ID único válido para modelos/decks Anki."""
    return random.randrange(1 << 30, 1 << 31)


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-2024-08-06", alias="OPENAI_MODEL")

    # Anki IDs
    anki_deck_id: int = Field(default_factory=_generate_anki_id, alias="ANKI_DECK_ID")
    anki_model_basic_id: int = Field(
        default_factory=_generate_anki_id, alias="ANKI_MODEL_BASIC_ID"
    )
    anki_model_cloze_id: int = Field(
        default_factory=_generate_anki_id, alias="ANKI_MODEL_CLOZE_ID"
    )
    anki_model_questao_id: int = Field(
        default_factory=_generate_anki_id, alias="ANKI_MODEL_QUESTAO_ID"
    )
    anki_model_jurisprudencia_id: int = Field(
        default_factory=_generate_anki_id, alias="ANKI_MODEL_JURISPRUDENCIA_ID"
    )

    # AnkiConnect
    anki_connect_url: str = Field(
        default="http://localhost:8765", alias="ANKI_CONNECT_URL"
    )

    # Versioning
    skill_version: str = Field(default="1.0.0", alias="SKILL_VERSION")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Instância global de configurações
settings = Settings()


class CardType(StrEnum):
    """Tipos de card suportados."""

    BASIC = "basic"
    BASIC_REVERSED = "basic_reversed"
    CLOZE = "cloze"
    QUESTAO = "questao"
    JURISPRUDENCIA = "jurisprudencia"


class Difficulty(StrEnum):
    """Níveis de dificuldade."""

    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"
