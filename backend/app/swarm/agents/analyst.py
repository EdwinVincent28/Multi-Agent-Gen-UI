import re
import time
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm, extract_text_content
from app.swarm.state import GraphState
from app.core.telemetry import record_node_telemetry, extract_tokens_used
from loguru import logger

def analyst_node(state: GraphState):
    """
    Takes clean JSON data from the state, performs statistical analysis, 
    and generates key business insights.
    """
    logger.info("--- ANALYST RUNNING ---")
    start_time = time.time()

    llm = get_llm(temperature=0.2) 

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Data Analyst in an autonomous AI swarm.
Your job is to analyze the provided clean JSON dataset and extract critical statistical summaries, trends, and actionable insights.

RULES:
1. Provide a concise breakdown of the dataset metrics (e.g., totals, averages, or ranges if applicable).
2. Highlight any key anomalies, outliers, or performance insights.
3. Present your findings using beautiful, highly structured Markdown with clear headings and bullet points.
4. Do NOT output any code or JSON. Output ONLY the textual analytical insights.
"""),
        ("user", "Clean Data JSON:\n\n{clean_data}")
    ])

    chain = prompt | llm
    
    response = chain.invoke({"clean_data": state["clean_data"]})

    insights = re.sub(r'<think>.*?</think>', '', extract_text_content(response.content), flags=re.DOTALL).strip()

    elapsed_time = time.time() - start_time
    tokens_used = extract_tokens_used(response)
    telemetry = record_node_telemetry(state.get("telemetry", {}), "analyst", elapsed_time, tokens_used, response_text=insights)

    return {"insights": insights, "telemetry": telemetry}