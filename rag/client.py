import os

from google import genai


def get_client(api_key=None):
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não encontrada.")
    return genai.Client(api_key=api_key)
