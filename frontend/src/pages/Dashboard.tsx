import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Activity, LogOut } from "lucide-react"

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

  const handleLogout = () => {
    localStorage.removeItem("jwt_token")
    navigate("/login")
  }

  const handleGenerate = async () => {
    const token = localStorage.getItem("jwt_token")
    if (!file || !token) return
    
    setIsLoading(true)
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

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem("jwt_token")
    if (!chatInput.trim() || !token) return
    
    setIsChatting(true)
    const payload = {
      session_id: sessionId,
      prompt: chatInput
    }

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/chat", {
        method: "POST",
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      })
      
      if (res.status === 401) {
        handleLogout()
        return
      }

      const data = await res.json()
      if (data.ui_code) {
        setGeneratedCode(data.ui_code)
      }
      setChatInput("") 
    } catch (error) {
      console.error("Chat failed:", error)
    } finally {
      setIsChatting(false)
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

        {generatedCode && (
          <div className="mt-8 space-y-4">
            <h2 className="text-xl font-bold text-slate-900">Generated Dashboard</h2>
            <SandboxRenderer codeString={generatedCode} data={dataset} />
    
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