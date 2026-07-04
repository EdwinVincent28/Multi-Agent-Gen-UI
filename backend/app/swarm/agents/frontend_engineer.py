from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.swarm.state import GraphState

def frontend_engineer_node(state: GraphState):
    """
    Ingests clean data and analytical insights, then synthesizes a secure,
    self-contained React component utilizing shadcn/ui and Tailwind CSS.
    """

    llm = get_llm(temperature=0.2) 

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert Frontend Architect specialized in React, Tailwind CSS, and shadcn/ui.
Your job is to look at a clean JSON dataset and its analytical insights, and generate a beautiful, completely self-contained interactive dashboard component.

RULES:
1. Return ONLY executable React component code. Do NOT wrap it in markdown code blocks (no ```jsx or ```tsx). Do NOT include explanations.
2. Use modern, functional React components using standard hooks (useState, useMemo) if interactivity is needed.
3. You MUST use shadcn/ui components to build the interface. Assume standard components are available via path aliases. 
   Example imports you should use:
   - import {{ Card, CardContent, CardHeader, CardTitle, CardDescription }} from "@/components/ui/card"
   - import {{ Badge }} from "@/components/ui/badge"
   - import {{ Button }} from "@/components/ui/button"
   - import {{ Table, TableBody, TableCell, TableHead, TableHeader, TableRow }} from "@/components/ui/table"
4. Style structural layouts and spacing using pure Tailwind CSS utility classes.
5. Assume standard `lucide-react` icons are available (e.g., import {{ Activity, Users }} from "lucide-react").
6. The component must be fully self-contained. Parse and embed the provided clean data directly inside the component block so it renders immediately without external fetching.
"""),
        ("user", "Clean Data:\n{clean_data}\n\nAnalytical Insights:\n{insights}")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "clean_data": state["clean_data"],
        "insights": state["insights"]
    })

    return {"ui_code": response.content}