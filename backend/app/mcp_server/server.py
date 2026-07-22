import os
import subprocess
import tempfile
import uuid
import re
import shutil
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GCP_DevOps_Server")

# Ensure Windows executes the correct CLI wrapper to prevent shell hangs
GCLOUD_CMD = "gcloud.cmd" if os.name == "nt" else "gcloud"

def create_vite_scaffold(target_dir: str, ui_code: str, dataset_json: str):
    """Copies the pre-configured React template and injects dynamic code and data."""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.abspath(os.path.join(current_dir, "..", "dashboard_template"))
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template directory not found at {template_path}. Please create it.")
        
    shutil.copytree(template_path, target_dir, dirs_exist_ok=True)
    
    # Prevent massive node_modules upload
    gcloudignore_path = os.path.join(target_dir, ".gcloudignore")
    with open(gcloudignore_path, "w") as f:
        f.write("node_modules/\n.git/\n")
    
    # --- NEW FIX: Strip Markdown formatting from the AI response ---
    ui_code = ui_code.strip()
    if ui_code.startswith("```"):
        ui_code = ui_code.split("\n", 1)[-1]  # Removes the first line (e.g., ```typescript)
    if ui_code.endswith("```"):
        ui_code = ui_code.rsplit("\n", 1)[0]  # Removes the last line (```)
    
    import_lines = []
    other_lines = []
    for line in ui_code.split('\n'):
        if line.startswith('import '):
            import_lines.append(line)
        else:
            other_lines.append(line)
            
    dynamic_data = f"\nconst data = {dataset_json};\n"
    
    final_code = "\n".join(import_lines) + "\n" + dynamic_data + "\n".join(other_lines)
    
    app_tsx_path = os.path.join(target_dir, "src", "App.tsx")
    with open(app_tsx_path, "w") as f:
        f.write(final_code)

@mcp.tool()
def deploy_dashboard_to_cloud(ui_code: str, dataset_json: str) -> str:
    """
    Copies a template Vite app, injects UI code and dynamic JSON data, 
    containerizes it, and deploys to Google Cloud Run.
    """
    try:
        key_path = os.path.abspath("gcp-key.json")
        if not os.path.exists(key_path):
            return f"Error: gcp-key.json not found at {key_path}"

        subprocess.run(
            f"{GCLOUD_CMD} auth activate-service-account --key-file={key_path} --quiet", 
            shell=True, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )
        subprocess.run(
            f"{GCLOUD_CMD} config set project gen-ui-swarm --quiet", 
            shell=True, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )

        service_name = f"gen-ui-dash-{uuid.uuid4().hex[:6]}"

        with tempfile.TemporaryDirectory() as temp_dir:

            create_vite_scaffold(temp_dir, ui_code, dataset_json)
            
            deploy_cmd = (
                f"{GCLOUD_CMD} run deploy {service_name} "
                f"--source {temp_dir} "
                f"--region us-central1 "
                f"--allow-unauthenticated "
                f"--port 80 "
                f"--quiet"
            )
            
            process = subprocess.run(
                deploy_cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL
            )
            
            output = process.stdout + process.stderr
            url_match = re.search(r'(https://[a-zA-Z0-9-.]+\.run\.app)', output)
            
            if url_match:
                return url_match.group(1)
            else:
                return f"Deployment succeeded, but couldn't parse URL. Output: {output}"
                
    except subprocess.CalledProcessError as e:
        return f"Deployment failed. Google Cloud Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

if __name__ == "__main__":
    mcp.run()