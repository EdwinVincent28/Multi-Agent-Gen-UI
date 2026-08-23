import re
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from app.core.llm import get_llm
from app.swarm.state import GraphState
from app.services.memory_service import save_dashboard_to_memory
from loguru import logger

def frontend_engineer_node(state: GraphState, config: RunnableConfig):
    """
    Ingests clean data, analytical insights, and visual blueprints, then synthesizes a secure,
    self-contained React component utilizing shadcn/ui and Tailwind CSS.
    Appends execution telemetry and handles feedback from the Evaluator node.
    """
    logger.info("--- FRONTEND ENGINEER RUNNING ---")
    start_time = time.time()

    llm = get_llm(temperature=0.2)

    clean_data = state.get("clean_data", [])
    columns = list(clean_data[0].keys()) if clean_data else []
    eval_feedback = state.get("eval_feedback", [])
    
    # Extract the new UI Blueprint from the Vision Node
    ui_blueprint = state.get("ui_blueprint")
    blueprint_instruction = ""
    if ui_blueprint:
        blueprint_instruction = f"""
CRITICAL INSTRUCTION: The user provided a visual wireframe blueprint. You MUST strictly structure your React layout and component hierarchy to match this exact JSON blueprint:
{ui_blueprint}
"""

    feedback_str = "\n".join([f"- {item}" for item in eval_feedback]) if eval_feedback else "None."

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Frontend Architect specialized in React, TypeScript, Tailwind CSS, and shadcn/ui.
Your job is to look at a clean JSON dataset, analytical insights, and UI blueprints, and generate a beautiful, completely self-contained interactive dashboard component.

ENVIRONMENT CONSTRAINTS:
- Framework: React with TypeScript (Vite).
- Styling: Tailwind CSS.
- Component Library: Shadcn UI + Lucide React icons.
- CRITICAL: You must import icons from "lucide-react". NEVER use "lucide-react-native" or "react-icons".
{blueprint_instruction}

CRITICAL SHADCN UI RULES (DO NOT HALLUCINATE):
1. TABLES: The <TableHeader> tag MUST wrap the <TableRow>. The <TableHead> tag represents the individual cell.
   Correct: <TableHeader><TableRow><TableHead>Title</TableHead></TableRow></TableHeader>
   Incorrect: <TableHead><TableRow><TableHeader>Title</TableHeader></TableRow></TableHead>
2. BADGES: Shadcn Badges DO NOT have a "primary" variant. You may ONLY use: "default", "secondary", "destructive", or "outline".

CRITICAL TYPESCRIPT RULES:
1. When using array methods like .reduce(), you MUST provide types to prevent compiler errors. 
   Example: data.reduce((acc: any, curr: any) => ..., {{}})

CRITICAL DATA RENDERING RULES (DO NOT HALLUCINATE COLUMNS):
1. Each item in the 'data' array is an OBJECT, not a primitive. The exact keys are given in "Dataset Columns" below.
2. NEVER render {{item}} directly inside a <TableCell> or anywhere else — 'item' is an object and this WILL crash with "Objects are not valid as a React child".
3. You MUST access specific fields by name, e.g. <TableCell>{{item.Region}}</TableCell>, using ONLY the keys listed in Dataset Columns.
4. <TableHead> labels MUST be the real column names from Dataset Columns — NEVER use generic placeholders like "Column 1" or "Value".
5. If Dataset Columns is empty, do not invent a data shape — render a clear empty/loading state instead.
         
DEPENDENCY & LIBRARY RULES:
1. You may import standard NPM packages (e.g., 'recharts', 'framer-motion', 'clsx'). The DevOps agent will automatically install any missing packages detected in your import statements.
2. For charting, 'recharts' is highly recommended. 
3. NEVER use <canvas>, <script> tags, or manual DOM chart initialization (e.g. document.getElementById, new Chart(...)) — this is a React-only sandbox.

GENERAL RULES:
1. Return ONLY executable React component code. 
2. CRITICAL STREAMING RULE: You must START YOUR RESPONSE DIRECTLY WITH `import React`. Do NOT output any conversational text, greetings, apologies, or explanations before or after the code. Do NOT wrap it in markdown code blocks (no ```jsx or ```tsx).
3. Use modern, functional React components using standard hooks (useState, useMemo) if interactivity is needed.
4. Assume standard components are available via path aliases. 
   Example imports you should use:
   - import {{ Card, CardContent, CardHeader, CardTitle, CardDescription }} from "@/components/ui/card"
   - import {{ Badge }} from "@/components/ui/badge"
   - import {{ Table, TableBody, TableCell, TableHead, TableHeader, TableRow }} from "@/components/ui/table"
5. CRITICAL: A global variable named 'data' containing the JSON array is already injected into your environment. You MUST use this global 'data' variable directly. DO NOT declare a local state variable named 'data' (e.g., never write const [data, setData] = useState(data)).

CRITICAL QUALITY EVALUATION FEEDBACK (CORRECT THESE ERRORS):
{feedback_str}

EDIT MODE RULES (SURGICAL REFACTORING):
If a USER PROMPT and PREVIOUS CODE are provided, you are in EDIT MODE. You must act as a strict Surgical Refactoring Engineer.
1. SURGICAL EDIT ONLY: You must preserve the exact structure, layout, grid columns, and data mappings of the PREVIOUS CODE.
2. NO UNSOLICITED CHANGES: Do NOT add new charts, duplicate existing charts, remove components, or change chart types unless the user explicitly asks you to in the USER PROMPT.
3. PRESERVE LOGIC: Only change the specific properties (e.g., fill color, text titles, borders, Tailwind classes) requested by the user. 
4. IGNORE RAW DATA DISTRACTIONS: Do not use the raw dataset or insights to invent new features during an edit. Focus ONLY on applying the user's request to the PREVIOUS CODE.
5. RETURN FULL COMPONENT: Apply the targeted fix, but return the ENTIRE updated React component code so it can be compiled directly.
"""),
        ("user", "Dataset Columns: {columns}\n\nClean Data:\n{clean_data}\n\nAnalytical Insights:\n{insights}\n\nPrevious Code:\n{previous_code}\n\nUser Prompt:\n{user_prompt}")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "columns": columns,
        "clean_data": clean_data,
        "insights": state.get("insights", ""),
        "previous_code": state.get("ui_code", "None provided."),
        "user_prompt": state.get("user_prompt", "None provided."),
        "feedback_str": feedback_str,
        "blueprint_instruction": blueprint_instruction
    })

    elapsed_time = time.time() - start_time
    
    tokens_used = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens_used = response.usage_metadata.get("total_tokens", 0)
    elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        tokens_used = response.response_metadata["token_usage"].get("total_tokens", 0)

    raw_content = response.content

    code_blocks = re.findall(
        r"```(?:tsx|jsx|typescript|javascript|ts|js)?\s*\n([\s\S]*?)```",
        raw_content
    )

    if code_blocks:
        ui_code = code_blocks[-1].strip()
    else:
        ui_code = raw_content.strip()

    thread_id = config.get("configurable", {}).get("thread_id")
    session_id = thread_id.split("_")[-1] if thread_id else None
    
    if session_id and ui_code:
        save_dashboard_to_memory(
            session_id=session_id,
            insights=str(state.get("insights", "")),
            ui_code=ui_code
        )

    telemetry = dict(state.get("telemetry", {}))
    is_first_pass = (state.get("retry_count", 0) == 0 and "baseline_latency" not in telemetry)

    if is_first_pass:
        telemetry["baseline_latency"] = round(telemetry.get("total_latency", 0.0) + elapsed_time, 2)
        telemetry["baseline_tokens"] = telemetry.get("total_tokens", 0) + tokens_used

    telemetry["total_latency"] = round(telemetry.get("total_latency", 0.0) + elapsed_time, 2)
    telemetry["total_tokens"] = telemetry.get("total_tokens", 0) + tokens_used

    return {
        "ui_code": ui_code,
        "telemetry": telemetry
    }