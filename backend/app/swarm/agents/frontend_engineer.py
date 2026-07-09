import re
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.swarm.state import GraphState

def frontend_engineer_node(state: GraphState):
    """
    Ingests clean data and analytical insights, then synthesizes a secure,
    self-contained React component utilizing shadcn/ui and Tailwind CSS.
    """
    print("--- FRONTEND ENGINEER RUNNING ---")

    llm = get_llm(temperature=0.2)

    clean_data = state.get("clean_data", [])
    columns = list(clean_data[0].keys()) if clean_data else []

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Frontend Architect specialized in React, TypeScript, Tailwind CSS, and shadcn/ui.
Your job is to look at a clean JSON dataset and its analytical insights, and generate a beautiful, completely self-contained interactive dashboard component.

ENVIRONMENT CONSTRAINTS:
- Framework: React with TypeScript (Vite).
- Styling: Tailwind CSS.
- Component Library: Shadcn UI + Lucide React icons.
- CRITICAL: You must import icons from "lucide-react". NEVER use "lucide-react-native" or "react-icons".

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
4. <TableHead> labels MUST be the real column names from Dataset Columns — NEVER use generic placeholders like "Column 1", "Column 2", "Value", or "Item".
5. If Dataset Columns is empty, do not invent a data shape — render a clear empty/loading state instead.
         
CRITICAL CHARTING RULES (DO NOT HALLUCINATE LIBRARIES):
1. The ONLY charting library available is "recharts". These components are pre-injected into your environment: BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer.
2. NEVER import or use "chart.js", "react-chartjs-2", or any other charting library — they are NOT available and will crash with "X is not defined".
3. NEVER use <canvas>, <script> tags, or manual DOM chart initialization (e.g. document.getElementById, new Chart(...)) — this is a React-only sandbox.
4. Example correct bar chart usage:
   <ResponsiveContainer width="100%" height={{300}}>
     <BarChart data={{chartData}}>
       <CartesianGrid strokeDasharray="3 3" />
       <XAxis dataKey="name" />
       <YAxis />
       <Tooltip />
       <Bar dataKey="value" fill="#8884d8" />
     </BarChart>
   </ResponsiveContainer>

GENERAL RULES:
1. Return ONLY executable React component code. Do NOT wrap it in markdown code blocks (no ```jsx or ```tsx). Do NOT include explanations.
2. Use modern, functional React components using standard hooks (useState, useMemo) if interactivity is needed.
3. Assume standard components are available via path aliases. 
   Example imports you should use:
   - import {{ Card, CardContent, CardHeader, CardTitle, CardDescription }} from "@/components/ui/card"
   - import {{ Badge }} from "@/components/ui/badge"
   - import {{ Button }} from "@/components/ui/button"
   - import {{ Table, TableBody, TableCell, TableHead, TableHeader, TableRow }} from "@/components/ui/table"
4. CRITICAL: A global variable named 'data' containing the JSON array is already injected into your environment. You MUST use this global 'data' variable directly. DO NOT declare a local state variable named 'data' (e.g., never write const [data, setData] = useState(data)).

EDIT MODE RULES:
If a USER PROMPT and PREVIOUS CODE are provided, you are in EDIT MODE.
Your job is to read the user's request, apply it to the PREVIOUS CODE, and return the ENTIRE updated React component. Do NOT remove existing features unless asked.
Preserve all existing data-field references (e.g. item.Region, item.Revenue) exactly as they were in PREVIOUS CODE unless the user explicitly asks to change what data is displayed.
"""),
        ("user", "Dataset Columns: {columns}\n\nClean Data:\n{clean_data}\n\nAnalytical Insights:\n{insights}\n\nPrevious Code:\n{previous_code}\n\nUser Prompt:\n{user_prompt}")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "columns": columns,
        "clean_data": clean_data,
        "insights": state.get("insights", ""),
        "previous_code": state.get("ui_code", "None provided."),
        "user_prompt": state.get("user_prompt", "None provided.")
    })

    raw_content = response.content

    code_blocks = re.findall(
        r"```(?:tsx|jsx|typescript|javascript|ts|js)?\s*\n([\s\S]*?)```",
        raw_content
    )

    if code_blocks:
        ui_code = code_blocks[-1].strip()
    else:
        ui_code = raw_content.strip()

    return {"ui_code": ui_code}