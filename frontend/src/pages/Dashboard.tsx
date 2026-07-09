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
    formData.append("session_id", "live_frontend_test_002")

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
          </div>
        )}
      </div>
    </div>
  )
}