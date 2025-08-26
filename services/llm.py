import os
from typing import Optional


def get_gemini_model(model_name: str = "gemini-2.5-flash", tools: Optional[dict] = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name, tools=tools) if tools else genai.GenerativeModel(model_name)


