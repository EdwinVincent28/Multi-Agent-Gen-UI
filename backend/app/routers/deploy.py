from fastapi import APIRouter, HTTPException
from app.models.schemas import DeployRequest
from app.swarm.agents.devops_agent import trigger_mcp_deployment

router = APIRouter()

@router.post("/")
async def deploy_dashboard(request: DeployRequest):
    """
    Receives finalized UI code from the frontend, connects to the local FastMCP server, 
    and manually triggers the Google Cloud Run containerization and deployment.
    """
    try:
        deployment_url = await trigger_mcp_deployment(request.ui_code)
        
        if "Deployment failed" in deployment_url or "Unexpected error" in deployment_url:
            raise HTTPException(status_code=500, detail=deployment_url)
            
        return {"deployment_url": deployment_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))