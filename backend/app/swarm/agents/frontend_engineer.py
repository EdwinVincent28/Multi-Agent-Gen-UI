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
"""),
        ("user", "Clean Data:\n{clean_data}\n\nAnalytical Insights:\n{insights}")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "clean_data": state["clean_data"],
        "insights": state["insights"]
    })

    return {"ui_code": response.content}