import sys
import asyncio
import json
import re
import subprocess
import os
from app.swarm.state import GraphState
from langchain_core.runnables.config import RunnableConfig
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from loguru import logger

def extract_and_install_dependencies(ui_code: str):
    """
    Scrapes the React code for import statements, extracts external NPM packages,
    and installs them locally in the Vite template directory.
    """
    logger.info("--- SCANNING FOR NEW DEPENDENCIES ---")
    
    matches = re.findall(r"(?:import\s+.*?\s+from\s+|import\s+)['\"]([^'\"]+)['\"]", ui_code)
    
    packages_to_install = set()
    for match in matches:
        if match.startswith('.') or match.startswith('@/'):
            continue
            
        parts = match.split('/')
        pkg = f"{parts[0]}/{parts[1]}" if match.startswith('@') and len(parts) > 1 else parts[0]
        
        if pkg not in ['react', 'react-dom']:
            packages_to_install.add(pkg)
            
    if packages_to_install:
        logger.info(f"DevOps Agent initiating npm install for: {packages_to_install}")
        
        template_dir = os.path.join(os.getcwd(), "app", "dashboard_template")
        
        try:
            subprocess.run(
                ["npm", "install", *list(packages_to_install)],
                cwd=template_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info("Dependencies successfully installed in template.")
        except subprocess.CalledProcessError as e:
            logger.error(f"NPM Install failed: {e.stderr.decode()}")
            raise Exception(f"Dependency resolution failed: {e.stderr.decode()}")
    else:
        logger.info("No external dependencies require installation.")


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
    Installs missing dependencies, extracts the finalized UI code and data, 
    and sends it to the MCP Server for deployment.
    """
    logger.info("--- DEVOPS AGENT RUNNING (ENVIRONMENT PREP & MCP) ---")
    
    ui_code = state.get("ui_code")
    clean_data = state.get("clean_data")
    
    if not ui_code:
        logger.info("No UI code found to deploy.")
        return {"deployment_url": None}
        
    if not clean_data:
        logger.info("No dataset found to inject.")
        return {"deployment_url": None, "errors": "Missing clean_data"}
        
    dataset_json = json.dumps(clean_data) if not isinstance(clean_data, str) else clean_data
        
    try:
        extract_and_install_dependencies(ui_code)
        
        deployed_url = asyncio.run(trigger_mcp_deployment(ui_code, dataset_json))
        
        logger.info(f"--- DEPLOYMENT SUCCESS: {deployed_url} ---")
        return {"deployment_url": deployed_url}
        
    except Exception as e:
        logger.error(f"--- MCP DEPLOYMENT ERROR: {e} ---")
        return {"deployment_url": None, "errors": str(e)}