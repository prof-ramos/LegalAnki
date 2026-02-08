"""Testes para o módulo de integração com AnkiConnect."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from legal_anki.anki_connect import AnkiConnectClient, AnkiConnectError


def _mock_response(result=None, error=None):
    """Cria um mock de resposta httpx."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"result": result, "error": error}
    return resp


class TestAnkiConnectInvoke:
    """Testes para o método _invoke (core)."""

    @patch("legal_anki.anki_connect.httpx.post")
    def test_invoke_sends_correct_payload(self, mock_post):
        """Envia payload JSON-RPC v6 correto."""
        mock_post.return_value = _mock_response(result="ok")
        client = AnkiConnectClient(url="http://localhost:8765")

        client._invoke("testAction", param1="value1")

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["action"] == "testAction"
        assert payload["version"] == 6
        assert payload["params"] == {"param1": "value1"}

    @patch("legal_anki.anki_connect.httpx.post")
    def test_invoke_returns_result(self, mock_post):
        """Retorna o campo result da resposta."""
        mock_post.return_value = _mock_response(result=["Deck1", "Deck2"])
        client = AnkiConnectClient()

        result = client._invoke("deckNames")
        assert result == ["Deck1", "Deck2"]

    @patch("legal_anki.anki_connect.httpx.post")
    def test_invoke_raises_on_api_error(self, mock_post):
        """Levanta AnkiConnectError quando a API retorna erro."""
        mock_post.return_value = _mock_response(error="deck not found")
        client = AnkiConnectClient()

        with pytest.raises(AnkiConnectError, match="deck not found"):
            client._invoke("deckNames")

    @patch("legal_anki.anki_connect.httpx.post")
    def test_invoke_raises_on_connection_error(self, mock_post):
        """Levanta AnkiConnectError em erro de conexão."""
        import httpx

        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = AnkiConnectClient()

        with pytest.raises(AnkiConnectError, match="Erro de conexão"):
            client._invoke("version")


class TestAnkiConnectQueries:
    """Testes para métodos de consulta."""

    @patch("legal_anki.anki_connect.httpx.post")
    def test_is_available_true(self, mock_post):
        """Retorna True quando Anki está disponível."""
        mock_post.return_value = _mock_response(result=6)
        client = AnkiConnectClient()

        assert client.is_available() is True

    @patch("legal_anki.anki_connect.httpx.post")
    def test_is_available_false_on_error(self, mock_post):
        """Retorna False quando Anki não está disponível."""
        import httpx

        mock_post.side_effect = httpx.ConnectError("Connection refused")
        client = AnkiConnectClient()

        assert client.is_available() is False

    @patch("legal_anki.anki_connect.httpx.post")
    def test_get_deck_names(self, mock_post):
        """Retorna lista de decks."""
        mock_post.return_value = _mock_response(result=["Default", "LegalAnki"])
        client = AnkiConnectClient()

        decks = client.get_deck_names()
        assert decks == ["Default", "LegalAnki"]

    @patch("legal_anki.anki_connect.httpx.post")
    def test_get_model_names(self, mock_post):
        """Retorna lista de modelos."""
        mock_post.return_value = _mock_response(result=["Basic", "Cloze"])
        client = AnkiConnectClient()

        models = client.get_model_names()
        assert models == ["Basic", "Cloze"]

    @patch("legal_anki.anki_connect.httpx.post")
    def test_create_deck(self, mock_post):
        """Cria deck e retorna ID."""
        mock_post.return_value = _mock_response(result=1234567890)
        client = AnkiConnectClient()

        deck_id = client.create_deck("Test Deck")
        assert deck_id == 1234567890


class TestAnkiConnectNotes:
    """Testes para adição de notas."""

    @patch("legal_anki.anki_connect.httpx.post")
    def test_add_note(self, mock_post):
        """Adiciona nota com campos corretos."""
        mock_post.return_value = _mock_response(result=9876543210)
        client = AnkiConnectClient()

        note_id = client.add_note(
            deck_name="LegalAnki",
            model_name="Basic",
            fields={"Front": "Pergunta?", "Back": "Resposta."},
            tags=["teste"],
        )

        assert note_id == 9876543210
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        note = payload["params"]["note"]
        assert note["deckName"] == "LegalAnki"
        assert note["modelName"] == "Basic"
        assert note["fields"]["Front"] == "Pergunta?"
        assert note["options"]["allowDuplicate"] is False

    @patch("legal_anki.anki_connect.httpx.post")
    def test_add_card_basic(self, mock_post, sample_card_basic):
        """Converte AnkiCard para nota e adiciona."""
        mock_post.return_value = _mock_response(result=1111111111)
        client = AnkiConnectClient()

        note_id = client.add_card(sample_card_basic, deck_name="Test")

        assert note_id == 1111111111
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        note = payload["params"]["note"]
        assert note["fields"]["Front"] == sample_card_basic.front
        assert note["fields"]["Back"] == sample_card_basic.back

    @patch("legal_anki.anki_connect.httpx.post")
    def test_add_cards_batch(self, mock_post, sample_cards):
        """Adiciona múltiplos cards em batch."""
        mock_post.return_value = _mock_response(result=[1, 2, 3, 4])
        client = AnkiConnectClient()

        result = client.add_cards_batch(sample_cards, deck_name="Test")

        assert len(result) == 4
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["action"] == "addNotes"
        assert len(payload["params"]["notes"]) == 4

    @patch("legal_anki.anki_connect.httpx.post")
    def test_add_cards_batch_partial_failure(self, mock_post, sample_cards):
        """Batch com falhas parciais retorna None nos falhos."""
        mock_post.return_value = _mock_response(result=[1, None, 3, None])
        client = AnkiConnectClient()

        result = client.add_cards_batch(sample_cards, deck_name="Test")

        assert result == [1, None, 3, None]

    @patch("legal_anki.anki_connect.httpx.post")
    def test_sync(self, mock_post):
        """Chama sync com AnkiWeb."""
        mock_post.return_value = _mock_response(result=None)
        client = AnkiConnectClient()

        client.sync()  # Não deve levantar exceção
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["action"] == "sync"
