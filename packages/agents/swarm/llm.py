import os
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama


def get_llm() -> BaseChatModel:
    model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    return ChatOllama(model=model, base_url=base_url, temperature=0.3)
