"""Protocolo (interface) para clientes LLM."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """
    Protocolo para clientes LLM.

    Define a interface que qualquer implementação de cliente LLM deve seguir,
    permitindo troca transparente de providers (OpenAI, Anthropic, local, etc.).
    """

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        """
        Gera uma resposta estruturada usando um modelo Pydantic.

        Args:
            system_prompt: Prompt do sistema com instruções
            user_message: Mensagem do usuário com o conteúdo
            response_model: Classe Pydantic para deserializar a resposta

        Returns:
            Instância do response_model com a resposta parseada
        """
        ...
