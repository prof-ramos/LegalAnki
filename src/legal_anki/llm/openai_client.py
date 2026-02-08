"""Cliente OpenAI com retry usando Tenacity."""

from __future__ import annotations

import logging
from typing import TypeVar

from openai import APIConnectionError, APIError, OpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAILLMClient:
    """
    Cliente OpenAI com retry e structured outputs.

    Implementa o protocolo LLMClient usando a API da OpenAI com
    retry automático via Tenacity para erros transientes.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-2024-08-06",
        max_retries: int = 3,
    ):
        """
        Inicializa o cliente OpenAI.

        Args:
            api_key: Chave da API OpenAI
            model: Modelo a usar (deve suportar structured outputs)
            max_retries: Número máximo de tentativas em caso de erro
        """
        # Desabilita retry interno do SDK, Tenacity controla
        self.client = OpenAI(api_key=api_key, max_retries=0)
        self.model = model
        self.max_retries = max_retries

    def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        """
        Gera resposta estruturada com retry automático.

        Args:
            system_prompt: Prompt do sistema
            user_message: Mensagem do usuário
            response_model: Modelo Pydantic para a resposta

        Returns:
            Instância do response_model parseada

        Raises:
            ValueError: Se o LLM não retornar resposta válida
            APIError: Se todas as tentativas falharem
        """
        return self._generate_with_retry(system_prompt, user_message, response_model)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
        retry=retry_if_exception_type((APIError, RateLimitError, APIConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number}/3 após erro: {retry_state.outcome.exception()}"
        ),
    )
    def _generate_with_retry(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        """Método interno com decorator de retry."""
        logger.debug(f"Chamando OpenAI API com modelo {self.model}")

        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=response_model,
        )

        result = response.choices[0].message.parsed

        if not result:
            refusal = response.choices[0].message.refusal
            if refusal:
                raise ValueError(f"LLM recusou gerar resposta: {refusal}")
            raise ValueError("LLM não retornou resposta válida")

        return result
