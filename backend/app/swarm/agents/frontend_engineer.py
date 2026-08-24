import re
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.config import RunnableConfig
from app.core.llm import get_llm, extract_text_content
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

    llm = get_llm(temperature=0.2, thinking_level="medium")

    clean_data = state.get("clean_data") or []
    columns = list(clean_data[0].keys()) if clean_data else []
    eval_feedback = state.get("eval_feedback", [])

    raw_previous_code = state.get("ui_code") or "None provided."
    raw_user_prompt = state.get("user_prompt") or "None provided."

    is_edit_mode = raw_user_prompt != "None provided." and raw_previous_code != "None provided."

    SAMPLE_ROWS = 8
    if is_edit_mode:
        sample_data = []
        sample_note = " (omitted in edit mode — see EDIT MODE RULES)"
    else:
        sample_data = clean_data[:SAMPLE_ROWS]
        total_rows = len(clean_data)
        sample_note = (
            f"\n(Showing {len(sample_data)} of {total_rows} total rows as a representative sample — "
            f"infer types and shape from this, do not assume this is the full dataset.)"
            if total_rows > SAMPLE_ROWS else ""
        )

    insights_for_prompt = "(omitted in edit mode — see EDIT MODE RULES)" if is_edit_mode else (state.get("insights") or "")

    ui_blueprint = state.get("ui_blueprint")
    blueprint_instruction = ""
    if ui_blueprint and not is_edit_mode:
        blueprint_instruction = f"""
CRITICAL INSTRUCTION: The user provided a visual wireframe blueprint as JSON below. This is not a loose suggestion — you MUST treat it as the exact spec for your layout:
1. Render EVERY item listed in the blueprint's grid.rows — every KPI, every chart, in the order given. Do not omit any.
2. Match each item's colSpan value to a Tailwind "col-span-{{N}}" class within a 12-column grid, exactly as specified — do not substitute a different layout (e.g. do not stack everything full-width if the blueprint specifies a multi-column row).
3. Match each chart's declared "type" (e.g. AreaChart, HorizontalBarChart) to the correct recharts component and orientation — an AreaChart must not become a table, a HorizontalBarChart must use layout="vertical".
4. Do NOT invent, add, or substitute any component, section, chart, or table that is not present in the blueprint JSON below — no extra "Recent Transactions" tables, no additional cards, nothing beyond what is explicitly listed.
5. Use the blueprint's theme colors (background, cardBackground, primaryColor, textPrimary, textSecondary) and header title/subtitle exactly as given.
6. Each item may include a "dataMapping" field describing what data it should show and how (e.g. "revenue summed by product category", "daily revenue trend over the date range"). Use this to decide which real column(s) from Dataset Columns to group/aggregate by and which aggregation (sum, average, count) to apply — do not guess a different grouping than what dataMapping describes, and do not fall back to hardcoded/sample numbers when real data is available.

Blueprint JSON:
{ui_blueprint}
"""

    feedback_str = "\n".join([f"- {item}" for item in eval_feedback]) if eval_feedback else "None."

    # previous_code still carries the full prior generated component in edit
    # mode — this one we keep, since edit mode genuinely needs it. Cap it
    # defensively so one oversized component can't blow the limit alone.
    MAX_PREV_CODE_CHARS = 14000  # ~3.5k tokens, rough estimate — leaves headroom for system prompt + edit request
    if len(raw_previous_code) > MAX_PREV_CODE_CHARS:
        previous_code_for_prompt = (
            raw_previous_code[:MAX_PREV_CODE_CHARS]
            + f"\n\n// ... TRUNCATED ({len(raw_previous_code) - MAX_PREV_CODE_CHARS} more characters not shown) ..."
        )
    else:
        previous_code_for_prompt = raw_previous_code

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
1. CRITICAL: The live preview (SandboxRenderer) runs your code in an in-browser sandbox with a FIXED, pre-bundled set of available imports — it cannot dynamically load a newly-npm-installed package the way the final deployed dashboard can. You MUST only import from this exact allowed set, or the live preview will break with a runtime "X is not defined" error even though the code looks syntactically correct:
   - "react" (React, useState, useMemo)
   - "recharts" (BarChart, Bar, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer)
   - "lucide-react" (any icon)
   - "@/components/ui/card" (Card, CardContent, CardHeader, CardTitle, CardDescription)
   - "@/components/ui/badge" (Badge)
   - "@/components/ui/button" (Button)
   - "@/components/ui/table" (Table, TableBody, TableCell, TableHead, TableHeader, TableRow)
   - "clsx" (default export, for conditional className logic)
   - "framer-motion" (motion, AnimatePresence — for transitions/animation polish only, do not overuse)
2. Do NOT import date-fns, lodash, or any other package not listed above, even though it is a "standard" NPM package — it will not be defined in the live preview sandbox.
3. For charting, 'recharts' is the only supported charting library.
4. NEVER use <canvas>, <script> tags, or manual DOM chart initialization (e.g. document.getElementById, new Chart(...)) — this is a React-only sandbox.

CRITICAL LAYOUT & SIZING RULE (READ CAREFULLY — THIS CAUSES INVISIBLE/BROKEN LAYOUTS IF IGNORED):
The live preview's Tailwind CSS is pre-compiled from this app's own static source files at build time. It does NOT re-scan your generated code, so any Tailwind utility class you use that doesn't already exist in the pre-built stylesheet (e.g. "grid-cols-12", "col-span-8", "h-[300px]") will be silently ignored — the className is applied but produces NO visual effect, with no error thrown. This causes two specific failures: a 12-column grid layout collapsing into plain stacked full-width blocks, and chart containers collapsing to zero height so ResponsiveContainer renders nothing.
To guarantee correct rendering, use INLINE STYLE OBJECTS (not Tailwind classes) for these two things specifically:
1. Grid container: style={{{{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}}}
2. Each grid item's span: style={{{{ gridColumn: `span ${{colSpanNumber}} / span ${{colSpanNumber}}` }}}}
3. Chart wrapper height (the div directly wrapping ResponsiveContainer): style={{{{ height: '300px', width: '100%' }}}}
You may continue using Tailwind classes for everything else (padding, colors, text sizing, rounded corners, shadows, borders) — those base utilities from the shadcn/ui component library ARE already compiled and available. Only grid structure and explicit pixel heights need inline styles.

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
        ("user", "Dataset Columns: {columns}\n\nSample Data:{sample_note}\n{clean_data}\n\nAnalytical Insights:\n{insights}\n\nPrevious Code:\n{previous_code}\n\nUser Prompt:\n{user_prompt}")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "columns": columns,
        "clean_data": sample_data,
        "sample_note": sample_note,
        "insights": insights_for_prompt,
        "previous_code": previous_code_for_prompt,
        "user_prompt": raw_user_prompt,
        "feedback_str": feedback_str,
        "blueprint_instruction": blueprint_instruction
    })

    elapsed_time = time.time() - start_time
    
    tokens_used = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens_used = response.usage_metadata.get("total_tokens", 0)
    elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        tokens_used = response.response_metadata["token_usage"].get("total_tokens", 0)

    raw_content = extract_text_content(response.content)

    raw_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)

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