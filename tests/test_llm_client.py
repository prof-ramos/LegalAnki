"""Testes para o módulo LLM."""

from unittest.mock import MagicMock, patch

from legal_anki.generator import generate_cards
from legal_anki.models import AnkiCard, CardResponse


class MockLLMClient:
    """Mock de LLMClient para testes."""

    def __init__(self, cards: list[AnkiCard] | None = None):
        self.cards = cards or [
            AnkiCard(
                front="Qual o prazo para propositura de ADI?",
                back="Não há prazo. A ADI pode ser proposta a qualquer tempo.",
                card_type="basic",
                tags=["controle_concentrado", "adi"],
                extra={"fundamento": "Art. 103 CF/88"},
            ),
        ]
        self.call_count = 0
        self.last_call = None

    def generate_structured(self, system_prompt, user_message, response_model):
        """Implementa o protocolo LLMClient."""
        self.call_count += 1
        self.last_call = {
            "system_prompt": system_prompt,
            "user_message": user_message,
            "response_model": response_model,
        }
        return CardResponse(cards=self.cards)


class TestLLMClientProtocol:
    """Testes para o protocolo LLMClient."""

    def test_mock_client_implements_protocol(self):
        """Mock client implementa a interface."""

        mock = MockLLMClient()

        # Verifica que tem os métodos necessários
        assert hasattr(mock, "generate_structured")
        assert callable(mock.generate_structured)


class TestGenerateCardsWithMockClient:
    """Testes de generate_cards com mock client."""

    def test_generate_cards_with_mock_returns_cards(self):
        """Geração com mock retorna cards."""
        mock = MockLLMClient()

        cards = generate_cards(
            text="Texto de teste sobre ADI",
            topic="controle_concentrado",
            llm_client=mock,
        )

        assert len(cards) == 1
        assert cards[0].front == "Qual o prazo para propositura de ADI?"
        assert mock.call_count == 1

    def test_generate_cards_passes_correct_params(self):
        """Parâmetros corretos são passados ao client."""
        mock = MockLLMClient()

        generate_cards(
            text="Texto sobre direitos fundamentais",
            topic="direitos_fundamentais",
            difficulty="dificil",
            include_legal_basis=True,
            llm_client=mock,
        )

        assert mock.last_call is not None
        assert "direitos_fundamentais" in mock.last_call["user_message"]
        assert mock.last_call["response_model"] == CardResponse

    def test_generate_cards_adds_topic_tag(self):
        """Topic tag é adicionada aos cards."""
        mock = MockLLMClient(
            cards=[
                AnkiCard(
                    front="Pergunta?",
                    back="Resposta com art. 5º CF",
                    card_type="basic",
                    tags=["stf"],
                    extra=None,
                ),
            ]
        )

        cards = generate_cards(
            text="Texto",
            topic="direitos_fundamentais",
            llm_client=mock,
        )

        assert "direitos_fundamentais" in cards[0].tags

    def test_generate_cards_adds_difficulty_tag(self):
        """Difficulty tag é adicionada."""
        mock = MockLLMClient()

        cards = generate_cards(
            text="Texto",
            topic="topic",
            difficulty="dificil",
            llm_client=mock,
        )

        assert "dificuldade_dificil" in cards[0].tags


class TestOpenAILLMClient:
    """Testes para OpenAILLMClient."""

    def test_client_initialization(self):
        """Cliente inicializa corretamente."""
        from legal_anki.llm.openai_client import OpenAILLMClient

        client = OpenAILLMClient(
            api_key="test-key",
            model="gpt-4o-mini",
            max_retries=5,
        )

        assert client.model == "gpt-4o-mini"
        assert client.max_retries == 5

    @patch("legal_anki.llm.openai_client.OpenAI")
    def test_client_calls_openai_parse(self, mock_openai_class):
        """Cliente chama OpenAI.beta.chat.completions.parse."""
        from legal_anki.llm.openai_client import OpenAILLMClient

        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.parsed = CardResponse(
            cards=[
                AnkiCard(
                    front="Q?",
                    back="A com art. 1º",
                    card_type="basic",
                    tags=["tag"],
                    extra=None,
                )
            ]
        )
        mock_message.refusal = None
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Execute
        client = OpenAILLMClient(api_key="test-key")
        result = client.generate_structured(
            system_prompt="System",
            user_message="User",
            response_model=CardResponse,
        )

        # Verify
        assert len(result.cards) == 1
        mock_client.beta.chat.completions.parse.assert_called_once()
