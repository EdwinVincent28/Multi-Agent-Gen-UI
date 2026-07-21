import os
import subprocess
import tempfile
import uuid
import re
from mcp.server.fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("GCP_DevOps_Server")

def create_vite_scaffold(target_dir: str, ui_code: str):
    """Scaffolds a lightweight React + Vite + Tailwind + TypeScript build environment."""
    
    os.makedirs(os.path.join(target_dir, "src"), exist_ok=True)
    
    # 1. package.json
    package_json = """{
      "name": "gen-ui-dashboard",
      "version": "1.0.0",
      "type": "module",
      "scripts": {
        "build": "vite build"
      },
      "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "lucide-react": "^0.263.1",
        "recharts": "^2.7.2"
      },
      "devDependencies": {
        "@vitejs/plugin-react": "^4.0.3",
        "vite": "^4.4.5"
      }
    }"""
    with open(os.path.join(target_dir, "package.json"), "w") as f:
        f.write(package_json)

    # 2. vite.config.js
    vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})"""
    with open(os.path.join(target_dir, "vite.config.js"), "w") as f:
        f.write(vite_config)

    # 3. index.html (Updated to load .tsx)
    index_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>"""
    with open(os.path.join(target_dir, "index.html"), "w") as f:
        f.write(index_html)

    # 4. src/main.tsx (Updated to TypeScript)
    main_tsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""
    with open(os.path.join(target_dir, "src", "main.tsx"), "w") as f:
        f.write(main_tsx)

    # 5. src/App.tsx (Injecting the LangGraph code, mock dataset, AND mock components)
    clean_code = re.sub(r'import {.*} from "@/components/ui/.*"\n?', '', ui_code)
    
    # Separate imports from the rest of the code to inject data safely
    import_lines = []
    other_lines = []
    for line in clean_code.split('\n'):
        if line.startswith('import '):
            import_lines.append(line)
        else:
            other_lines.append(line)
            
    # Inject a fallback dataset and mock UI components so it doesn't crash
    mock_data_and_components = """
// --- Mock Data ---
const data = [
  { Revenue: "4200", Units_Sold: "120", Region: "North America" },
  { Revenue: "5100", Units_Sold: "150", Region: "Europe" },
  { Revenue: "6800", Units_Sold: "200", Region: "Asia" },
  { Revenue: "8900", Units_Sold: "250", Region: "South America" }
];

// --- Mock UI Components ---
const Card = ({ children, className, ...props }) => <div className={`bg-white border border-slate-200 rounded-xl shadow-sm ${className || ''}`} {...props}>{children}</div>;
const CardHeader = ({ children, className, ...props }) => <div className={`p-6 pb-2 ${className || ''}`} {...props}>{children}</div>;
const CardTitle = ({ children, className, ...props }) => <h3 className={`text-lg font-semibold tracking-tight ${className || ''}`} {...props}>{children}</h3>;
const CardContent = ({ children, className, ...props }) => <div className={`p-6 pt-0 ${className || ''}`} {...props}>{children}</div>;
const CardDescription = ({ children, className, ...props }) => <p className={`text-sm text-slate-500 ${className || ''}`} {...props}>{children}</p>;
const Button = ({ children, className, ...props }) => <button className={`inline-flex items-center justify-center rounded-md text-sm font-medium bg-slate-900 text-white hover:bg-slate-800 h-10 px-4 py-2 ${className || ''}`} {...props}>{children}</button>;
const Table = ({ children, className, ...props }) => <div className="w-full overflow-auto"><table className={`w-full caption-bottom text-sm ${className || ''}`} {...props}>{children}</table></div>;
const TableHeader = ({ children, className, ...props }) => <thead className={`border-b border-slate-200 ${className || ''}`} {...props}>{children}</thead>;
const TableBody = ({ children, className, ...props }) => <tbody className={`[&_tr:last-child]:border-0 ${className || ''}`} {...props}>{children}</tbody>;
const TableRow = ({ children, className, ...props }) => <tr className={`border-b border-slate-200 transition-colors hover:bg-slate-50 ${className || ''}`} {...props}>{children}</tr>;
const TableHead = ({ children, className, ...props }) => <th className={`h-12 px-4 text-left align-middle font-medium text-slate-500 ${className || ''}`} {...props}>{children}</th>;
const TableCell = ({ children, className, ...props }) => <td className={`p-4 align-middle ${className || ''}`} {...props}>{children}</td>;
const Badge = ({ children, className, ...props }) => <div className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors ${className || ''}`} {...props}>{children}</div>;
"""
    # Reassemble the file: Imports -> Mock Data & Components -> Component Code
    final_code = "\n".join(import_lines) + "\n" + mock_data_and_components + "\n".join(other_lines)
    
    with open(os.path.join(target_dir, "src", "App.tsx"), "w") as f:
        f.write(final_code)

    # 6. Dockerfile (Multi-stage: Build with Node, Serve with Nginx)
    dockerfile = """# Stage 1: Build the React App
FROM node:18-alpine as build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]"""
    
    with open(os.path.join(target_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)


@mcp.tool()
def deploy_dashboard_to_cloud(ui_code: str) -> str:
    """
    Scaffolds a Vite app, containerizes the React UI code, 
    and deploys it to Google Cloud Run.
    """
    try:
        key_path = os.path.abspath("gcp-key.json")
        if not os.path.exists(key_path):
            return f"Error: gcp-key.json not found at {key_path}"

        # 1. Authenticate with GCP
        subprocess.run(
            f"gcloud auth activate-service-account --key-file={key_path} --quiet", 
            shell=True, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )
        subprocess.run(
            "gcloud config set project gen-ui-swarm --quiet", 
            shell=True, check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL
        )

        # 2. Generate a unique service name for this deployment
        service_name = f"gen-ui-dash-{uuid.uuid4().hex[:6]}"

        # 3. Create a temporary directory to build the app
        with tempfile.TemporaryDirectory() as temp_dir:
            
            # Scaffold the files
            create_vite_scaffold(temp_dir, ui_code)
            
            # 4. Trigger Google Cloud Run Deployment
            deploy_cmd = (
                f"gcloud run deploy {service_name} "
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
            
            # 5. Extract the live URL from Google's terminal output (Updated Regex)
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