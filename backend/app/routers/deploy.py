import json
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.schemas import DeployRequest
from app.swarm.agents.devops_agent import trigger_mcp_deployment

router = APIRouter()

deployment_jobs = {}

async def run_background_deployment(job_id: str, ui_code: str, dataset_json: str):
    """The long-running deployment task executed in the background."""
    deployment_jobs[job_id] = {"status": "building", "url": None, "error": None}
    
    try:
        deployment_url = await trigger_mcp_deployment(ui_code, dataset_json)
        
        if "Deployment failed" in deployment_url or "Unexpected error" in deployment_url:
            deployment_jobs[job_id] = {"status": "failed", "error": deployment_url}
        else:
            deployment_jobs[job_id] = {"status": "completed", "url": deployment_url}
            
    except Exception as e:
        deployment_jobs[job_id] = {"status": "failed", "error": str(e)}

@router.post("")
async def deploy_dashboard(request: DeployRequest, background_tasks: BackgroundTasks):
    """
    Receives finalized UI code, generates a job ID, and offloads the 
    Cloud Run deployment to a background task so the API returns instantly.
    """
    job_id = str(uuid.uuid4())
    dataset_json = json.dumps(request.clean_data)
    
    background_tasks.add_task(
        run_background_deployment, 
        job_id, 
        request.ui_code, 
        dataset_json
    )
    
    return {"job_id": job_id, "status": "building"}

@router.get("/status/{job_id}")
async def get_deployment_status(job_id: str):
    """Allows the frontend to poll for the current deployment status."""
    job = deployment_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Deployment job not found")
    return job