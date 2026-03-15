import os
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI


def get_llm() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("Set LLM_API_KEY in .env")
    if provider == "groq":
        return ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key, temperature=0.3)
    return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0.3)
