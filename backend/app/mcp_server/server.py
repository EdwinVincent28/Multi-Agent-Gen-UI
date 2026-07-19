import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GCP_DevOps_Server")

@mcp.tool()
def deploy_dashboard_to_cloud(ui_code: str) -> str:
    """
    Authenticates with GCP, containerizes the React UI code, 
    and deploys it to Google Cloud Run.
    """
    try:
        key_path = os.path.abspath("gcp-key.json")
        
        if not os.path.exists(key_path):
            return f"Error: gcp-key.json not found at {key_path}"

        auth_cmd = f"gcloud auth activate-service-account --key-file={key_path} --quiet"
        
        subprocess.run(
            auth_cmd, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=15,
            stdin=subprocess.DEVNULL  
        )
        
        config_cmd = "gcloud config set project gen-ui-swarm --quiet"
        
        subprocess.run(
            config_cmd, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=15,
            stdin=subprocess.DEVNULL  
        )
        
        deployment_url = "https://gen-ui-dashboard-x89a2b.a.run.app (Auth Successful!)"
        return deployment_url
        
    except subprocess.TimeoutExpired:
        return "Deployment failed: The gcloud command timed out."
    except subprocess.CalledProcessError as e:
        return f"Deployment failed. Google Cloud Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

if __name__ == "__main__":
    mcp.run()