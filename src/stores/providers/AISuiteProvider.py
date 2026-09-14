import os
import aisuite as ai
from src.stores.llm.LLMInterface import LLMInterface
from src.helpers.config import settings


class AISuiteProvider(LLMInterface):
    def __init__(self, model_name: str = None, client=None):
        self.model_name = model_name or settings.MODEL

        cohere_key = settings.get_cohere_key()
        if cohere_key:
            os.environ["CO_API_KEY"] = cohere_key.strip().strip("'\"")
            os.environ["COHERE_API_KEY"] = cohere_key.strip().strip("'\"")

        if settings.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY.strip().strip("'\"")

        self.client = client or ai.Client()
        self.tools = None

    def bind_tools(self, tools: list):
        self.tools = tools
        return self

    def generate(self, prompt: str, system_instruction: str = "", use_tools: bool = True) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0,
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content