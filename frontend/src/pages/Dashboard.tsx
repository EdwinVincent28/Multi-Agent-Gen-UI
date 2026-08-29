import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Activity, LogOut, Cloud, ExternalLink, Image as ImageIcon, Radio, MessageCircle } from "lucide-react"

import SandboxRenderer from "@/components/SandboxRenderer"

// Reads a File as plain text. Used for the CSV, which travels over the
// WebSocket as a JSON string field instead of multipart/FormData.
function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}

type DataSourceMode = "csv" | "twitch"

export default function Dashboard() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)

  const [dataSourceMode, setDataSourceMode] = useState<DataSourceMode>("csv")
  const [twitchChannel, setTwitchChannel] = useState("")
  const [isLiveConnected, setIsLiveConnected] = useState(false)

  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageBase64, setImageBase64] = useState<string | null>(null)
  
  const [isLoading, setIsLoading] = useState(false)
  const [generationStatus, setGenerationStatus] = useState<string | null>(null)
  const [generatedCode, setGeneratedCode] = useState<string | null>(null)
  const [dataset, setDataset] = useState<any[] | null>(null)

  const [sessionId] = useState(() => crypto.randomUUID())

  const [chatInput, setChatInput] = useState("")
  const [isChatting, setIsChatting] = useState(false)

  const [twitchQuestionInput, setTwitchQuestionInput] = useState("")
  const [isAskingTwitchQuestion, setIsAskingTwitchQuestion] = useState(false)
  const [twitchQaHistory, setTwitchQaHistory] = useState<
    { question: string; answer: string; hasContext: boolean }[]
  >([])

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

    let csvContent: string
    try {
      csvContent = await readFileAsText(file)
    } catch (error) {
      console.error("Failed to read CSV file:", error)
      return
    }

    setIsLoading(true)
    setGenerationStatus("Connecting...")
    setGeneratedCode("")
    setDataset(null)
    setDeploymentUrl(null)

    const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/ws/generate/${sessionId}`)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        token: token,
        csv_content: csvContent,
        uploaded_image_base64: imageBase64 || undefined,
      }))
    }

    ws.onmessage = (event) => {
      const raw = event.data

      if (raw === "<END_OF_STREAM>") {
        ws.close()
        return
      }

      let message: any
      try {
        message = JSON.parse(raw)
      } catch {
        console.error("Received non-JSON message from /ws/generate:", raw)
        return
      }

      switch (message.type) {
        case "status":
          setGenerationStatus(message.message)
          break

        case "code_chunk":
          setGeneratedCode((prev) => (prev || "") + message.content)
          break

        case "final":
          if (message.ui_code) {
            setGeneratedCode(message.ui_code)
          }
          setDataset(message.data ?? null)
          setGenerationStatus(null)
          break

        case "error":
          console.error("Generation error:", message.message)
          setGenerationStatus(null)
          break

        default:
          console.warn("Unknown message type from /ws/generate:", message)
      }
    }

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error)
      setIsLoading(false)
      setGenerationStatus(null)
    }

    ws.onclose = () => {
      setIsLoading(false)
      setGenerationStatus(null)
    }
  }

  // Twitch mode's counterpart to handleGenerate. Shares the same message
  // protocol (status/code_chunk/final) for the initial generation phase,
  // but — unlike /ws/generate — the connection stays open afterward and
  // keeps receiving "data_update" messages as the live session continues.
  // There's no "<END_OF_STREAM>" sentinel here, since the whole point is
  // that the stream doesn't end until the user navigates away.
  const handleConnectTwitch = () => {
    const token = localStorage.getItem("jwt_token")
    if (!twitchChannel.trim() || !token) return

    setIsLoading(true)
    setGenerationStatus("Connecting to Twitch...")
    setGeneratedCode("")
    setDataset(null)
    setDeploymentUrl(null)
    setIsLiveConnected(false)

    const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/ws/twitch/${sessionId}`)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        token: token,
        channel: twitchChannel.trim(),
        uploaded_image_base64: imageBase64 || undefined,
      }))
    }

    ws.onmessage = (event) => {
      let message: any
      try {
        message = JSON.parse(event.data)
      } catch {
        console.error("Received non-JSON message from /ws/twitch:", event.data)
        return
      }

      switch (message.type) {
        case "status":
          setGenerationStatus(message.message)
          break

        case "code_chunk":
          setGeneratedCode((prev) => (prev || "") + message.content)
          break

        case "final":
          if (message.ui_code) {
            setGeneratedCode(message.ui_code)
          }
          setDataset(message.data ?? null)
          setGenerationStatus(null)
          setIsLoading(false)
          setIsLiveConnected(true)
          break

        case "data_update":
          // Ongoing live updates, arriving after "final" — the dashboard
          // component itself re-renders off this prop change, no new
          // code generation involved.
          setDataset(message.data ?? null)
          break

        case "error":
          console.error("Twitch generation error:", message.message)
          setGenerationStatus(null)
          setIsLoading(false)
          break

        default:
          console.warn("Unknown message type from /ws/twitch:", message)
      }
    }

    ws.onerror = (error) => {
      console.error("Twitch WebSocket Error:", error)
      setIsLoading(false)
      setIsLiveConnected(false)
      setGenerationStatus(null)
    }

    ws.onclose = () => {
      setIsLoading(false)
      setIsLiveConnected(false)
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

  // Ask-your-dashboard Q&A (Twitch mode only, RAG over indexed live
  // session context). A plain REST call, unlike generation/chat — a
  // single retrieve-then-answer request has no meaningful streaming
  // stages to show progress for.
  const handleAskTwitchQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    const token = localStorage.getItem("jwt_token")
    const question = twitchQuestionInput.trim()
    if (!question || !token) return

    setIsAskingTwitchQuestion(true)
    setTwitchQuestionInput("")

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/twitch/ask", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ session_id: sessionId, question }),
      })

      if (res.status === 401) {
        handleLogout()
        return
      }

      const data = await res.json()
      setTwitchQaHistory((prev) => [
        ...prev,
        { question, answer: data.answer, hasContext: data.has_context },
      ])
    } catch (error) {
      console.error("Twitch Q&A request failed:", error)
      setTwitchQaHistory((prev) => [
        ...prev,
        { question, answer: "Something went wrong answering that — please try again.", hasContext: false },
      ])
    } finally {
      setIsAskingTwitchQuestion(false)
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
            <CardDescription>Upload a CSV, or connect to a live Twitch channel, to trigger the LangGraph swarm.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">

            {/* Mode toggle */}
            <div className="flex gap-2 p-1 bg-slate-100 rounded-lg w-fit">
              <button
                onClick={() => setDataSourceMode("csv")}
                disabled={isLoading}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  dataSourceMode === "csv"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Upload CSV
              </button>
              <button
                onClick={() => setDataSourceMode("twitch")}
                disabled={isLoading}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                  dataSourceMode === "twitch"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                <Radio size={14} /> Live Twitch Channel
              </button>
            </div>

            {dataSourceMode === "csv" ? (
              <>
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
                  {isLoading ? (generationStatus || "Swarm is generating UI...") : "Generate Dashboard"}
                </Button>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Twitch Channel Name</label>
                  <Input
                    type="text"
                    placeholder="e.g. tarik"
                    value={twitchChannel}
                    onChange={(e) => setTwitchChannel(e.target.value)}
                    disabled={isLoading || isLiveConnected}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700 flex items-center gap-1">
                    <ImageIcon size={14} /> Upload Wireframe (Optional)
                  </label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    disabled={isLoading || isLiveConnected}
                  />
                </div>

                {imagePreview && (
                  <div className="mt-2 border border-slate-200 rounded-lg p-2 bg-white inline-block">
                    <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">Wireframe Preview</p>
                    <img src={imagePreview} alt="Wireframe" className="h-32 w-auto rounded object-contain" />
                  </div>
                )}

                {isLiveConnected && (
                  <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5 w-fit">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Live — connected to #{twitchChannel}
                  </div>
                )}

                <Button
                  onClick={handleConnectTwitch}
                  disabled={!twitchChannel.trim() || isLoading || isLiveConnected}
                  className="w-full mt-4"
                >
                  {isLoading ? (generationStatus || "Connecting...") : isLiveConnected ? "Connected" : "Connect & Generate Dashboard"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {(generatedCode !== null || isChatting || isLoading) && (
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

            {/* Live status banner during first generation — separate from
                the code stream itself, since these steps happen before
                frontend_engineer writes any code. */}
            {isLoading && generationStatus && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-sm text-blue-700 flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                {generationStatus}
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

            {/* Twitch mode only — the RAG backend only has indexed
                context for live Twitch sessions, so showing this for a
                CSV dashboard would just hit the "not enough data" case
                every time, which isn't useful. */}
            {dataSourceMode === "twitch" && (
              <Card className="mt-4 border-purple-200 bg-purple-50/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg text-purple-800 flex items-center gap-2">
                    <MessageCircle size={18} /> Ask Your Dashboard
                  </CardTitle>
                  <CardDescription className="text-purple-600">
                    Ask about what's happened in the stream so far (e.g., "why did viewers spike earlier?")
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {twitchQaHistory.length > 0 && (
                    <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                      {twitchQaHistory.map((entry, i) => (
                        <div key={i} className="text-sm space-y-1">
                          <p className="font-medium text-slate-800">{entry.question}</p>
                          <p className={entry.hasContext ? "text-slate-600" : "text-slate-400 italic"}>
                            {entry.answer}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <form onSubmit={handleAskTwitchQuestion} className="flex gap-2">
                    <Input
                      value={twitchQuestionInput}
                      onChange={(e) => setTwitchQuestionInput(e.target.value)}
                      placeholder="Ask a question about the stream..."
                      disabled={isAskingTwitchQuestion}
                      className="bg-white"
                    />
                    <Button type="submit" disabled={isAskingTwitchQuestion || !twitchQuestionInput.trim()}>
                      {isAskingTwitchQuestion ? "Thinking..." : "Ask"}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}