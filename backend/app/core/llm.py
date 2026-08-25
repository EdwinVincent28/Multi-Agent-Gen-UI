import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def extract_text_content(content):
    """
    Normalizes an LLM response's .content into a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""

def get_llm(temperature=0.0, thinking_level="low"):
    """
    Initializes the Google Gemini client for text/code generation
    (analyst, frontend_engineer, evaluator nodes).
    """

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash"),
        temperature=temperature,
        max_output_tokens=65536,
        thinking_level=thinking_level,
        api_key=os.getenv("GEMINI_API_KEY")
    ).with_retry(
        stop_after_attempt=5,
        wait_exponential_jitter=True
    )

def get_vision_llm(temperature=0.0):
    """
    Initializes the Google Gemini client for vision (wireframe extraction).
    """
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_VISION_MODEL", "gemini-3.6-flash"),
        temperature=temperature,
        thinking_level="low",
        api_key=os.getenv("GEMINI_API_KEY")
    ).with_retry(
        stop_after_attempt=5,
        wait_exponential_jitter=True
    )