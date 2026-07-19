import sys
import asyncio
from app.swarm.state import GraphState
from langchain_core.runnables.config import RunnableConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def trigger_mcp_deployment(ui_code: str) -> str:
    """Handles the asynchronous connection to the MCP Server."""
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u","app/mcp_server/server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "deploy_dashboard_to_cloud", 
                arguments={"ui_code": ui_code}
            )
            
            return result.content[0].text

def devops_agent_node(state: GraphState, config: RunnableConfig):
    """
    Extracts the finalized UI code and sends it to the MCP Server for deployment.
    """
    print("--- DEVOPS AGENT RUNNING (MCP CLIENT INITIALIZED) ---")
    
    ui_code = state.get("ui_code")
    if not ui_code:
        print("No UI code found to deploy.")
        return {"deployment_url": None}
        
    try:
        deployed_url = asyncio.run(trigger_mcp_deployment(ui_code))
        
        print(f"--- DEPLOYMENT SUCCESS: {deployed_url} ---")
        return {"deployment_url": deployed_url}
        
    except Exception as e:
        print(f"--- MCP DEPLOYMENT ERROR: {e} ---")
        return {"deployment_url": None, "errors": str(e)}