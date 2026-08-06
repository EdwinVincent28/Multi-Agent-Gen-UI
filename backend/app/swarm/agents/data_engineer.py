import csv
import io
from app.swarm.state import GraphState
from loguru import logger

def data_engineer_node(state: GraphState):
    """
    Deterministically parses raw CSV text into a clean Python list of dictionaries.
    Bypasses LLM token limits entirely.
    """
    logger.info("--- DATA ENGINEER RUNNING (DETERMINISTIC) ---")
    raw_text = state.get("raw_data", "")

    try:
        reader = csv.DictReader(io.StringIO(raw_text))
        clean_data = [row for row in reader]
        return {"clean_data": clean_data, "errors": None}
        
    except Exception as e:
        return {"errors": f"Data Engineer failed to parse CSV: {str(e)}"}