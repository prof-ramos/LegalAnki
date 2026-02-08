"""Cliente para integração com AnkiConnect API v6."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests

from .config import settings
from .models import get_model_for_card_type
from .serializers import map_card_to_fields

if TYPE_CHECKING:
    from .generator import AnkiCard

logger = logging.getLogger(__name__)


class AnkiConnectError(Exception):
    """Erro na comunicação com AnkiConnect."""

    pass


class AnkiConnectClient:
    """Cliente para API AnkiConnect v6."""

    def __init__(self, url: str | None = None):
        """
        Inicializa o cliente AnkiConnect.

        Args:
            url: URL do AnkiConnect. Default usa settings.
        """
        self.url = url or settings.anki_connect_url

    def _invoke(self, action: str, **params: Any) -> Any:
        """
        Invoca uma ação no AnkiConnect.

        Args:
            action: Nome da ação
            **params: Parâmetros da ação

        Returns:
            Resultado da ação

        Raises:
            AnkiConnectError: Se houver erro na requisição
        """
        payload = {
            "action": action,
            "version": 6,
            "params": params,
        }

        try:
            response = requests.post(self.url, json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise AnkiConnectError(
                f"Erro de conexão com AnkiConnect em {self.url}: {e}"
            ) from e

        result = response.json()

        if result.get("error"):
            raise AnkiConnectError(f"AnkiConnect error: {result['error']}")

        return result.get("result")

    def is_available(self) -> bool:
        """Verifica se o Anki está rodando com AnkiConnect."""
        try:
            version = self._invoke("version")
            logger.info(f"AnkiConnect versão {version} disponível")
            return True
        except AnkiConnectError:
            return False

    def get_deck_names(self) -> list[str]:
        """Retorna lista de nomes de decks."""
        return self._invoke("deckNames")

    def get_model_names(self) -> list[str]:
        """Retorna lista de nomes de modelos (note types)."""
        return self._invoke("modelNames")

    def create_deck(self, deck_name: str) -> int:
        """
        Cria um novo deck.

        Args:
            deck_name: Nome do deck

        Returns:
            ID do deck criado
        """
        return self._invoke("createDeck", deck=deck_name)

    def add_note(
        self,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str],
        allow_duplicate: bool = False,
    ) -> int:
        """
        Adiciona uma nota ao Anki.

        Args:
            deck_name: Nome do deck
            model_name: Nome do modelo/note type
            fields: Dicionário campo -> valor
            tags: Lista de tags
            allow_duplicate: Se True, permite duplicatas

        Returns:
            ID da nota criada
        """
        return self._invoke(
            "addNote",
            note={
                "deckName": deck_name,
                "modelName": model_name,
                "fields": fields,
                "tags": tags,
                "options": {"allowDuplicate": allow_duplicate},
            },
        )

    def add_notes_batch(
        self,
        notes: list[dict[str, Any]],
    ) -> list[int | None]:
        """
        Adiciona múltiplas notas de uma vez.

        Args:
            notes: Lista de notas no formato AnkiConnect

        Returns:
            Lista de IDs das notas criadas (None para falhas)
        """
        return self._invoke("addNotes", notes=notes)

    def sync(self) -> None:
        """Sincroniza o Anki com AnkiWeb."""
        self._invoke("sync")
        logger.info("Sincronização com AnkiWeb concluída")

    def add_card(
        self,
        card: "AnkiCard",
        deck_name: str,
        allow_duplicate: bool = False,
    ) -> int:
        """
        Adiciona um AnkiCard ao Anki via AnkiConnect.

        Args:
            card: Card a adicionar
            deck_name: Nome do deck
            allow_duplicate: Se True, permite duplicatas

        Returns:
            ID da nota criada
        """
        model = get_model_for_card_type(card.card_type)
        field_values = map_card_to_fields(card)
        field_names = [f["name"] for f in model.fields]

        # Monta dicionário de campos
        fields = dict(zip(field_names, field_values))

        return self.add_note(
            deck_name=deck_name,
            model_name=model.name,
            fields=fields,
            tags=card.tags,
            allow_duplicate=allow_duplicate,
        )

    def add_cards_batch(
        self,
        cards: list["AnkiCard"],
        deck_name: str,
        allow_duplicate: bool = False,
    ) -> list[int | None]:
        """
        Adiciona múltiplos AnkiCards ao Anki.

        Args:
            cards: Lista de cards a adicionar
            deck_name: Nome do deck
            allow_duplicate: Se True, permite duplicatas

        Returns:
            Lista de IDs das notas criadas
        """
        notes = []

        for card in cards:
            model = get_model_for_card_type(card.card_type)
            field_values = map_card_to_fields(card)
            field_names = [f["name"] for f in model.fields]
            fields = dict(zip(field_names, field_values))

            notes.append(
                {
                    "deckName": deck_name,
                    "modelName": model.name,
                    "fields": fields,
                    "tags": card.tags,
                    "options": {"allowDuplicate": allow_duplicate},
                }
            )

        result = self.add_notes_batch(notes)
        logger.info(
            f"Adicionados {sum(1 for r in result if r is not None)} cards via AnkiConnect"
        )
        return result
