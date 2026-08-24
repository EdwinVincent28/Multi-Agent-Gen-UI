import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Activity, LogOut, Cloud, ExternalLink, Image as ImageIcon } from "lucide-react"

import SandboxRenderer from "@/components/SandboxRenderer"

export default function Dashboard() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageBase64, setImageBase64] = useState<string | null>(null)
  
  const [isLoading, setIsLoading] = useState(false)
  const [generatedCode, setGeneratedCode] = useState<string | null>(null)
  const [dataset, setDataset] = useState<any[] | null>(null)

  const [sessionId] = useState(() => crypto.randomUUID())

  const [chatInput, setChatInput] = useState("")
  const [isChatting, setIsChatting] = useState(false)

  const [isDeploying, setIsDeploying] = useState(false)
  const [deploymentUrl, setDeploymentUrl] = useState<string | null>(null)

  const handleLogout = () => {
    localStorage.removeItem("jwt_token")
    navigate("/login")
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImagePreview(URL.createObjectURL(file))
      
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1]
        setImageBase64(base64String)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleGenerate = async () => {
    const token = localStorage.getItem("jwt_token")
    if (!file || !token) return
    
    setIsLoading(true)
    setDeploymentUrl(null)
    const formData = new FormData()
    formData.append("file", file)
    formData.append("session_id", sessionId)
    
    if (imageBase64) {
      formData.append("uploaded_image_base64", imageBase64)
    }

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/generate", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      })
      
      if (res.status === 401) {
        handleLogout() 
        return
      }

      const data = await res.json()
      if (data.ui_code) {
        setGeneratedCode(data.ui_code)
        setDataset(data.data) 
      }
    } catch (error) {
      console.error("Generation failed:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem("jwt_token")
    if (!chatInput.trim() || !token) return
    
    setIsChatting(true)
    setGeneratedCode("")
    setDeploymentUrl(null)
    
    const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/ws/chat/${sessionId}`)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        token: token,
        prompt: chatInput
      }))
      setChatInput("") 
    }

    ws.onmessage = (event) => {
      const chunk = event.data

      if (chunk === "<END_OF_STREAM>") {
        ws.close()
        return
      }
      
      if (chunk.startsWith("Error:") || chunk.startsWith("Fatal Error:")) {
        console.error("Backend streaming error:", chunk)
        ws.close()
        return
      }

      setGeneratedCode((prev) => (prev || "") + chunk)
    }

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error)
      setIsChatting(false)
    }

    ws.onclose = () => {
      setIsChatting(false)
    }
  }

  const handleDeployToCloud = async () => {
    const token = localStorage.getItem("jwt_token")
    if (!generatedCode || !token) return
    
    setIsDeploying(true)
    setDeploymentUrl(null)
    
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/deploy", {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          ui_code: generatedCode,
          clean_data: dataset || []
        })
      })
      
      const data = await res.json()
      
      if (data.job_id) {
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`http://127.0.0.1:8000/api/v1/deploy/status/${data.job_id}`);
            
            if (statusRes.ok) {
              const statusData = await statusRes.json();

              if (statusData.status === "completed") {
                setDeploymentUrl(statusData.url);
                setIsDeploying(false);
                clearInterval(pollInterval);
              } else if (statusData.status === "failed") {
                console.error("Deployment failed:", statusData.error);
                setIsDeploying(false);
                clearInterval(pollInterval);
              }
            }
          } catch (pollError) {
            console.error("Polling error:", pollError);
            setIsDeploying(false);
            clearInterval(pollInterval);
          }
        }, 3000);
      }
    } catch (error) {
      console.error("Cloud deployment request failed:", error)
      setIsDeploying(false)
    }
  }

  return (
    <div className="p-8 bg-slate-50 min-h-screen font-sans">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-slate-900">Workspace</h1>
          <Button variant="outline" size="sm" onClick={handleLogout} className="flex items-center gap-2">
            <LogOut size={16} /> Logout
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="text-blue-500" /> Data Ingestion Engine
            </CardTitle>
            <CardDescription>Upload a CSV and an optional wireframe to trigger the LangGraph swarm.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">1. Upload Dataset (CSV)</label>
                <Input type="file" accept=".csv,.json" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 flex items-center gap-1">
                  <ImageIcon size={14} /> 2. Upload Wireframe (Optional)
                </label>
                <Input type="file" accept="image/*" onChange={handleImageUpload} />
              </div>
            </div>

            {imagePreview && (
              <div className="mt-4 border border-slate-200 rounded-lg p-2 bg-white inline-block">
                <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">Wireframe Preview</p>
                <img src={imagePreview} alt="Wireframe" className="h-32 w-auto rounded object-contain" />
              </div>
            )}

            <Button onClick={handleGenerate} disabled={!file || isLoading} className="w-full mt-4">
              {isLoading ? "Swarm is generating UI..." : "Generate Dashboard"}
            </Button>
          </CardContent>
        </Card>

        {(generatedCode !== null || isChatting) && (
          <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900">Generated Dashboard</h2>
              <Button 
                onClick={handleDeployToCloud} 
                disabled={isDeploying || isChatting || isLoading}
                className="bg-slate-900 hover:bg-slate-800 text-white flex items-center gap-2"
              >
                {isDeploying ? "Containerizing..." : "Deploy to Google Cloud"}
                {!isDeploying && <Cloud size={16} />}
              </Button>
            </div>
            
            {/* Cloud Deployment Success Banner */}
            {deploymentUrl && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between mt-4 mb-4">
                <div className="flex items-center gap-3">
                  <Cloud className="text-green-600" size={24} />
                  <div>
                    <h3 className="text-green-800 font-semibold">Live in Google Cloud</h3>
                    <p className="text-green-600 text-sm">Your dashboard has been successfully containerized and deployed.</p>
                  </div>
                </div>
                <Button onClick={() => window.open(deploymentUrl, '_blank')} className="bg-green-600 hover:bg-green-700 text-white gap-2">
                  View Live App <ExternalLink size={16} />
                </Button>
              </div>
            )}

            <SandboxRenderer 
              codeString={generatedCode || ""} 
              data={dataset} 
              isStreaming={isChatting || isLoading} 
            />
    
            <Card className="mt-4 border-blue-200 bg-blue-50/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-blue-800">Iterate with AI</CardTitle>
                <CardDescription className="text-blue-600">
                  Ask the Frontend Engineer to modify the dashboard (e.g., "Change the table to a bar chart")
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleChat} className="flex gap-2">
                  <Input 
                    value={chatInput} 
                    onChange={(e) => setChatInput(e.target.value)} 
                    placeholder="Type your modification request here..." 
                    disabled={isChatting}
                    className="bg-white"
                  />
                  <Button type="submit" disabled={isChatting || !chatInput.trim()}>
                    {isChatting ? "Updating..." : "Send Request"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}