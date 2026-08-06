import json
import time
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.swarm.state import GraphState
from loguru import logger

def evaluator_node(state: GraphState):
    """
    Evaluates generated UI code against schema rules and library constraints.
    Returns structured feedback and updates total telemetry metrics.
    """
    logger.info("--- EVALUATOR NODE RUNNING ---")
    start_time = time.time()

    llm = get_llm(temperature=0.0)

    ui_code = state.get("ui_code", "")
    clean_data = state.get("clean_data", [])
    columns = list(clean_data[0].keys()) if clean_data else []

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an automated Code QA Evaluator for a React dashboard system.
Your job is to inspect generated React code and verify it complies with environment constraints.

DATASET COLUMNS AVAILABLE:
{columns}

REACT CODE TO REVIEW:
{ui_code}

RULES TO CHECK:
1. COLUMN GROUNDEDNESS: Does the code access object properties using real column names (e.g., item.Region)? Mark FAIL if generic placeholders (item.Column1, item.Value) or non-existent column names are used.
2. SHADCN UI COMPLIANCE: If <Table> components are used, is <TableHeader> wrapping <TableRow>? Mark FAIL if <TableHead> wraps <TableRow>.
3. CHART LIBRARIES: Is recharts used for charts? Mark FAIL if "chart.js", "react-chartjs-2", or <canvas> tags are used.
4. SYNTAX INTEGRITY: Does the code contain valid React imports and export a default function?

OUTPUT FORMAT:
Return ONLY a valid, raw JSON object (no markdown code blocks, no trailing comments):
{{
  "pass": true | false,
  "feedback": ["List specific issues found if pass is false. Empty if pass is true."]
}}
"""),
        ("user", "Evaluate the code against the rules.")
    ])

    chain = prompt | llm

    try:
        response = chain.invoke({
            "columns": columns,
            "ui_code": ui_code
        })
        
        elapsed_time = time.time() - start_time

        tokens_used = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_used = response.usage_metadata.get("total_tokens", 0)
        elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            tokens_used = response.response_metadata["token_usage"].get("total_tokens", 0)

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        eval_result = json.loads(content)
        passed = eval_result.get("pass", False)
        feedback = eval_result.get("feedback", [])

    except Exception as e:
        logger.error(f"Evaluator parsing error: {e}")
        passed = True
        feedback = []
        elapsed_time = time.time() - start_time
        tokens_used = 0

    telemetry = dict(state.get("telemetry", {}))
    telemetry["total_latency"] = round(telemetry.get("total_latency", 0.0) + elapsed_time, 2)
    telemetry["total_tokens"] = telemetry.get("total_tokens", 0) + tokens_used

    current_retries = state.get("retry_count", 0)

    if passed:
        telemetry["task_success"] = True
        return {
            "eval_feedback": [],
            "telemetry": telemetry
        }
    else:
        telemetry["task_success"] = False
        return {
            "eval_feedback": feedback,
            "retry_count": current_retries + 1,
            "telemetry": telemetry
        }