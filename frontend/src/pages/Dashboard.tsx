import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Activity, LogOut, Cloud, ExternalLink } from "lucide-react"

import SandboxRenderer from "@/components/SandboxRenderer"

export default function Dashboard() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
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

  const handleGenerate = async () => {
    const token = localStorage.getItem("jwt_token")
    if (!file || !token) return
    
    setIsLoading(true)
    setDeploymentUrl(null)
    const formData = new FormData()
    formData.append("file", file)
    formData.append("session_id", sessionId)

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
        body: JSON.stringify({ ui_code: generatedCode })
      })
      
      const data = await res.json()
      if (data.deployment_url) {
        setDeploymentUrl(data.deployment_url)
      }
    } catch (error) {
      console.error("Cloud deployment failed:", error)
    } finally {
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
            <CardDescription>Upload a CSV to trigger the LangGraph generation swarm.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input type="file" accept=".csv,.json" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <Button onClick={handleGenerate} disabled={!file || isLoading} className="w-full">
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