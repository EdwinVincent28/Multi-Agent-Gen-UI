from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.swarm.state import GraphState

def analyst_node(state: GraphState):
    """
    Takes clean JSON data from the state, performs statistical analysis, 
    and generates key business insights.
    """
    print("--- ANALYST RUNNING ---")

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

    return {"insights": response.content}