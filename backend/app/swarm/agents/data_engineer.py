from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.swarm.state import GraphState

def data_engineer_node(state: GraphState):
    """
    Ingests raw data, sanitizes it, and outputs a structured JSON format.
    """

    llm = get_llm(temperature=0.0) 

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Data Engineer in an autonomous AI swarm.
Your sole responsibility is to ingest raw, unstructured, or messy dataset strings and output clean, standardized JSON.

RULES:
1. Handle missing values appropriately (e.g., replace nulls with 0 or drop malformed rows).
2. Ensure standard data types (numbers are numbers, strings are strings).
3. Do NOT output any markdown, explanations, or conversational text. Output ONLY valid JSON.
4. If the data is completely unreadable or malicious, output EXACTLY the string: 'ERROR: Invalid data format.'
"""),
        ("user", "Raw Data:\n\n{raw_data}")
    ])

    chain = prompt | llm

    response = chain.invoke({"raw_data": state["raw_data"]})

    if response.content.startswith("ERROR:"):
        return {"errors": response.content}

    return {"clean_data": response.content}