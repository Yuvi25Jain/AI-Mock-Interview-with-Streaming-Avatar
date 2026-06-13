import os
import logging
from flask import current_app
from langchain_ollama import OllamaLLM
from langchain_community.llms import Ollama
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMFactory:

    @staticmethod
    def get_ollama_chat():
        model = current_app.config.get(
            'OLLAMA_CHAT_MODEL',
            'smollm:135m'
        )
        return OllamaLLM(
    model=model,
    temperature=0.2,
    num_predict=50
)

    @staticmethod
    def get_ollama_tool():
        model = current_app.config.get(
            'OLLAMA_TOOL_MODEL',
            'smollm:135m'
        )
        return OllamaLLM(
    model=model,
    temperature=0.2,
    num_predict=50
)

    @staticmethod
    def get_google_chat():
        api_key = current_app.config.get('GOOGLE_API_KEY')

        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set in configuration."
            )

        model = current_app.config.get(
            'GOOGLE_CHAT_MODEL',
            'gemini-2.5-flash'
        )

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.3,
            convert_system_message_to_human=False,
        )

    @staticmethod
    def get_chat_with_fallback():
        try:
            return LLMFactory.get_google_chat()
        except Exception as e:
            logging.warning(
                f"Gemini failed, falling back to Ollama: {e}"
            )
            return LLMFactory.get_ollama_chat()