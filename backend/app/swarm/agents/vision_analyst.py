from langchain_core.messages import HumanMessage
from app.swarm.state import GraphState
from app.core.llm import get_vision_llm
from loguru import logger

def vision_analyst_node(state: GraphState):
    logger.info("--- VISION ANALYST RUNNING (GEMINI FLASH) ---")
    
    image_data = state.get("uploaded_image_base64")
    
    if not image_data:
        logger.info("No image provided. Skipping vision analysis.")
        return {"ui_blueprint": None}
    
    vision_llm = get_vision_llm(temperature=0.1)
    
    prompt = """
    You are an expert UI/UX Architect. Look at this wireframe/screenshot.
    Extract the layout into a strict JSON blueprint. 
    Identify the charts needed (e.g., BarChart, LineChart), the grid structure, and the color theme.
    Return ONLY valid JSON without markdown wrapping.
    """
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
    )
    
    try:
        response = vision_llm.invoke([message])
        return {"ui_blueprint": response.content}
    except Exception as e:
        logger.error(f"Vision Analyst Failed: {str(e)}")
        return {"errors": f"Vision analysis failed: {str(e)}"}