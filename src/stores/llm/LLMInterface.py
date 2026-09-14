from abc import ABC, abstractmethod
from typing import List, Optional


class LLMInterface(ABC):
    """Abstract interface for LLM provider implementations."""

    @abstractmethod
    def bind_tools(self, tools: list):
        """Bind tool definitions to the LLM client."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_instruction: str = "", use_tools: bool = True) -> str:
        """Generate a response text from the LLM."""
        pass
