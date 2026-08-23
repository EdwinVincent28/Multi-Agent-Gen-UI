import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def get_llm(temperature=0.0):
    """
    Initializes the Groq client. 
    Temperature is parameterized to allow different agents to have different creativity levels.
    """

    return ChatGroq(
        temperature=temperature,
        model_name="llama-3.3-70b-versatile",
        streaming=True,
        api_key=os.getenv("GROQ_API_KEY")
    )

def get_vision_llm(temperature=0.0):
    """
    Initializes the free Google Gemini client.
    Used strictly by the Vision Analyst node for sketch-to-code extraction.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=temperature,
        api_key=os.getenv("GEMINI_API_KEY")
    )