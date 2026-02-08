"""Modelos Anki especializados para Direito Constitucional."""

import genanki
from pydantic import BaseModel, Field, field_validator

from .config import CardType, settings

# =============================================================================
# Modelos Pydantic para Cards
# =============================================================================


class AnkiCard(BaseModel):
    """Modelo de um card Anki gerado."""

    front: str = Field(
        min_length=1, description="Texto da frente do card (pergunta ou cloze)"
    )
    back: str = Field(min_length=1, description="Texto do verso do card (resposta)")
    card_type: CardType = Field(description="Tipo do card")
    tags: list[str] = Field(
        default_factory=list, description="Lista de tags para o card"
    )
    extra: dict | None = Field(
        default=None,
        description="Campos adicionais dependendo do tipo (banca, ano, tribunal, fundamento, etc.)",
    )

    @field_validator("front", "back", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        """Remove espaços extras e valida que o campo não está vazio."""
        if not isinstance(v, str):
            raise ValueError("Campo deve ser uma string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Campo não pode ser vazio")
        return stripped


class CardResponse(BaseModel):
    """Resposta estruturada do LLM com lista de cards."""

    cards: list[AnkiCard] = Field(description="Lista de cards gerados")


# =============================================================================
# Modelos Genanki (templates Anki)
# =============================================================================


# CSS compartilhado para todos os modelos
CARD_CSS = """
.card {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 18px;
    text-align: left;
    color: #333;
    background-color: #fafafa;
    padding: 20px;
    line-height: 1.6;
}

.question {
    font-size: 20px;
    font-weight: 500;
    margin-bottom: 15px;
}

.answer {
    margin-top: 15px;
}

.metadata {
    font-size: 13px;
    color: #666;
    margin-top: 10px;
    padding: 8px;
    background-color: #f0f0f0;
    border-radius: 4px;
}

.fundamento {
    margin-top: 15px;
    padding: 10px;
    background-color: #e8f4f8;
    border-left: 4px solid #0077b6;
    font-size: 14px;
    color: #333;
}

.cloze {
    font-weight: bold;
    color: #0077b6;
}

.extra {
    margin-top: 15px;
    font-size: 14px;
    color: #555;
    border-top: 1px solid #ddd;
    padding-top: 10px;
}

hr#answer {
    border: none;
    border-top: 2px solid #0077b6;
    margin: 20px 0;
}
"""


def create_basic_model() -> genanki.Model:
    """Cria modelo Basic (Pergunta/Resposta)."""
    return genanki.Model(
        model_id=settings.anki_model_basic_id,
        name="LegalAnki Basic",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="question">{{Front}}</div>',
                "afmt": """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="answer">{{Back}}</div>
                """,
            }
        ],
        css=CARD_CSS,
    )


def create_cloze_model() -> genanki.Model:
    """Cria modelo Cloze para lacunas."""
    return genanki.Model(
        model_id=settings.anki_model_cloze_id,
        name="LegalAnki Cloze",
        model_type=genanki.Model.CLOZE,
        fields=[
            {"name": "Text"},
            {"name": "Extra"},
        ],
        templates=[
            {
                "name": "Cloze",
                "qfmt": "{{cloze:Text}}",
                "afmt": """
                    {{cloze:Text}}
                    {{#Extra}}
                    <div class="extra">{{Extra}}</div>
                    {{/Extra}}
                """,
            }
        ],
        css=CARD_CSS,
    )


def create_questao_model() -> genanki.Model:
    """Cria modelo para questões de concurso."""
    return genanki.Model(
        model_id=settings.anki_model_questao_id,
        name="LegalAnki Questao",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Banca"},
            {"name": "Ano"},
            {"name": "Cargo"},
            {"name": "Fundamento"},
        ],
        templates=[
            {
                "name": "Questão Concurso",
                "qfmt": """
                    <div class="question">{{Front}}</div>
                    <div class="metadata">
                        {{#Banca}}{{Banca}}{{/Banca}}
                        {{#Ano}} - {{Ano}}{{/Ano}}
                        {{#Cargo}} - {{Cargo}}{{/Cargo}}
                    </div>
                """,
                "afmt": """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="answer">{{Back}}</div>
                    {{#Fundamento}}
                    <div class="fundamento">
                        <strong>📚 Fundamento:</strong><br>
                        {{Fundamento}}
                    </div>
                    {{/Fundamento}}
                """,
            }
        ],
        css=CARD_CSS,
    )


def create_jurisprudencia_model() -> genanki.Model:
    """Cria modelo para súmulas e julgados."""
    return genanki.Model(
        model_id=settings.anki_model_jurisprudencia_id,
        name="LegalAnki Jurisprudencia",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Tribunal"},
            {"name": "DataJulgamento"},
            {"name": "Tema"},
            {"name": "FundamentoLegal"},
        ],
        templates=[
            {
                "name": "Jurisprudência",
                "qfmt": """
                    <div class="question">{{Front}}</div>
                    <div class="metadata">
                        {{#Tribunal}}🏛️ {{Tribunal}}{{/Tribunal}}
                        {{#Tema}} | 📌 {{Tema}}{{/Tema}}
                    </div>
                """,
                "afmt": """
                    {{FrontSide}}
                    <hr id="answer">
                    <div class="answer">{{Back}}</div>
                    {{#DataJulgamento}}
                    <div class="metadata">📅 Julgado em: {{DataJulgamento}}</div>
                    {{/DataJulgamento}}
                    {{#FundamentoLegal}}
                    <div class="fundamento">
                        <strong>📜 Base Legal:</strong><br>
                        {{FundamentoLegal}}
                    </div>
                    {{/FundamentoLegal}}
                """,
            }
        ],
        css=CARD_CSS,
    )


# Mapeamento de tipo para modelo - usa CardType Enum
_MODEL_FACTORY = {
    CardType.BASIC: create_basic_model,
    CardType.BASIC_REVERSED: create_basic_model,  # Usa mesmo modelo, gera 2 notes
    CardType.CLOZE: create_cloze_model,
    CardType.QUESTAO: create_questao_model,
    CardType.JURISPRUDENCIA: create_jurisprudencia_model,
}


def get_model_for_card_type(card_type: str) -> genanki.Model:
    """Retorna o modelo Anki apropriado para o tipo de card."""
    factory = _MODEL_FACTORY.get(card_type)
    if not factory:
        raise ValueError(f"Tipo de card desconhecido: {card_type}")
    return factory()


def get_field_names_for_card_type(card_type: str) -> list[str]:
    """Retorna os nomes dos campos para um tipo de card."""
    model = get_model_for_card_type(card_type)
    return [f["name"] for f in model.fields]
