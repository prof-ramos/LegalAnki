"""Abstração de clientes LLM para geração de cards."""

from .openai_client import OpenAILLMClient
from .protocol import LLMClient

__all__ = ["LLMClient", "OpenAILLMClient"]
