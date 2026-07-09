import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

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