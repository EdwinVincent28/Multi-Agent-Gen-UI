import base64
import io
import time
from langchain_core.messages import HumanMessage
from app.swarm.state import GraphState
from app.core.llm import get_vision_llm, extract_text_content
from app.core.telemetry import record_node_telemetry, extract_tokens_used
from loguru import logger

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


MAX_ENCODED_BYTES = 1024 * 1024

MAX_RAW_BYTES = int(MAX_ENCODED_BYTES * 0.7)
MAX_DIMENSION = 1600 


def _compress_image_base64(image_b64: str) -> str:
    """
    Decodes a base64 image, resizes and/or re-compresses it as JPEG if
    needed to fit under Gemini's inline Part size limit, and returns a new
    base64 string. Returns the original string unchanged if PIL isn't
    available or the image is already small enough.
    """
    raw_bytes = base64.b64decode(image_b64)

    if len(raw_bytes) <= MAX_RAW_BYTES:
        return image_b64

    if not PIL_AVAILABLE:
        logger.warning(
            "Image exceeds safe size for Gemini's inline Part limit and "
            "Pillow is not installed to compress it — sending as-is, this "
            "may fail with 'Part exceeded maximum size'. Run: "
            "pip install Pillow"
        )
        return image_b64

    img = Image.open(io.BytesIO(raw_bytes))

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.convert("RGBA").split()[-1] if img.mode != "P" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    for quality in (85, 75, 65, 50):
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        compressed_bytes = buffer.getvalue()
        if len(compressed_bytes) <= MAX_RAW_BYTES:
            logger.info(
                f"Compressed wireframe image: {len(raw_bytes)} -> "
                f"{len(compressed_bytes)} bytes (quality={quality})"
            )
            return base64.b64encode(compressed_bytes).decode("utf-8")

    logger.warning(
        f"Could not compress image under {MAX_RAW_BYTES} bytes even at "
        f"quality=50 (got {len(compressed_bytes)} bytes) — sending anyway."
    )
    return base64.b64encode(compressed_bytes).decode("utf-8")


def vision_analyst_node(state: GraphState):
    logger.info("--- VISION ANALYST RUNNING (GEMINI FLASH) ---")
    start_time = time.time()

    if state.get("ui_code"):
        logger.info(
            "Thread already has a ui_code (this is an edit, not a "
            "fresh generation) — skipping vision analysis, its output "
            "would be discarded anyway."
        )
        return {}

    image_data = state.get("uploaded_image_base64")
    
    if not image_data:
        logger.info("No image provided. Skipping vision analysis.")
        return {"ui_blueprint": None}

    image_data = _compress_image_base64(image_data)

    vision_llm = get_vision_llm(temperature=0.1)
    
    prompt = """
    You are an expert UI/UX Architect. Look at this wireframe/screenshot of a data dashboard.
    Extract the layout into a strict JSON blueprint that a frontend engineer will use to
    rebuild this exact dashboard using a real dataset.

    For EVERY visual element you see, identify:
    1. The COMPONENT TYPE — be specific: "KPI Card", "LineChart", "BarChart" (and whether
       vertical or horizontal), "PieChart", "AreaChart", "Table", "Badge", etc. Do not use a
       vague catch-all like "chart" or "widget".
    2. What DATA it appears to represent and how that data is grouped/aggregated — e.g.
       "total revenue summed across all records", "revenue broken down by region",
       "units sold grouped by product category over time", "satisfaction score per region".
       Be as specific as the wireframe's labels/legend/axis text allow. This detail is
       critical: it tells the engineer which column to group by and which aggregation
       (sum, average, count) to use — do not skip it or leave it generic.
    3. Its position and size in the grid (colSpan out of 12 columns).
    4. Any visible title, subtitle, or axis/legend labels, verbatim where legible.

    Also identify the overall theme (background color, card background, primary accent
    color, primary/secondary text color) and the header title/subtitle.

    Return a JSON object with this shape (extend as needed for what you actually see):
    {
      "theme": { "background": "...", "cardBackground": "...", "primaryColor": "...", "textPrimary": "...", "textSecondary": "..." },
      "header": { "title": "...", "subtitle": "..." },
      "grid": {
        "columns": 12,
        "rows": [
          {
            "id": "...",
            "items": [
              {
                "id": "...",
                "type": "KPI Card | LineChart | BarChart (vertical/horizontal) | PieChart | AreaChart | Table | ...",
                "colSpan": <number>,
                "title": "...",
                "dataMapping": "plain-language description of exactly what data this shows and how it's grouped/aggregated — e.g. 'revenue summed by product category' or 'daily revenue trend over the date range'",
                "value": "... (for KPI cards, if a sample value is visible)"
              }
            ]
          }
        ]
      }
    }

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
        elapsed_time = time.time() - start_time
        tokens_used = extract_tokens_used(response)
        blueprint_text = extract_text_content(response.content)
        telemetry = record_node_telemetry(state.get("telemetry", {}), "vision_analyst", elapsed_time, tokens_used, response_text=blueprint_text)
        return {"ui_blueprint": blueprint_text, "telemetry": telemetry}
    except Exception as e:
        logger.error(f"Vision Analyst Failed: {str(e)}")
        return {"errors": f"Vision analysis failed: {str(e)}"}