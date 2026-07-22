import sys
import asyncio
import json
from app.swarm.state import GraphState
from langchain_core.runnables.config import RunnableConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def trigger_mcp_deployment(ui_code: str, dataset_json: str) -> str:
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
                arguments={
                    "ui_code": ui_code,
                    "dataset_json": dataset_json
                }
            )
            
            return result.content[0].text

def devops_agent_node(state: GraphState, config: RunnableConfig):
    """
    Extracts the finalized UI code and data, and sends it to the MCP Server for deployment.
    """
    print("--- DEVOPS AGENT RUNNING (MCP CLIENT INITIALIZED) ---")
    
    ui_code = state.get("ui_code")
    clean_data = state.get("clean_data")
    
    if not ui_code:
        print("No UI code found to deploy.")
        return {"deployment_url": None}
        
    if not clean_data:
        print("No dataset found to inject.")
        return {"deployment_url": None, "errors": "Missing clean_data"}
        
    dataset_json = json.dumps(clean_data) if not isinstance(clean_data, str) else clean_data
        
    try:
        deployed_url = asyncio.run(trigger_mcp_deployment(ui_code, dataset_json))
        
        print(f"--- DEPLOYMENT SUCCESS: {deployed_url} ---")
        return {"deployment_url": deployed_url}
        
    except Exception as e:
        print(f"--- MCP DEPLOYMENT ERROR: {e} ---")
        return {"deployment_url": None, "errors": str(e)}