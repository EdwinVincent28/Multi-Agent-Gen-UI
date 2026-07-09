import React, { useState, useMemo, useEffect } from "react"
import { LiveProvider, LiveError, LivePreview } from "react-live"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import * as LucideIcons from "lucide-react"
import { Eye, Code } from "lucide-react"
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts"

const scope = {
  React,
  useState,
  useMemo,
  ...LucideIcons, 
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Badge,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,   
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
}

export default function SandboxRenderer({ 
  codeString, 
  data, 
  isStreaming 
}: { 
  codeString: string, 
  data: any[] | null,
  isStreaming?: boolean 
}) {
  const [view, setView] = useState<"preview" | "code">("preview")
  useEffect(() => {
    if (isStreaming) {
      setView("code")
    } else {
      const timer = setTimeout(() => setView("preview"), 300)
      return () => clearTimeout(timer)
    }
  }, [isStreaming])

  const cleanCode = useMemo(() => {
    if (!codeString) return ""

    let processed = codeString
      .replace(/```[a-zA-Z]*\n?/g, "")
      .replace(/```/g, "")
      .split('\n')
      .filter(line => !line.trim().startsWith('import'))
      .join('\n')
      .replace(/export default \w+;?/g, "")
      .trim()

    processed += "\n\nrender(<Dashboard />);"

    return processed
  }, [codeString])

  const dynamicScope = {
    ...scope,  
    data   
  }

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm flex flex-col">
      <div className="flex border-b border-slate-200 bg-slate-100/50">
        <button
          onClick={() => setView("preview")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            view === "preview" 
              ? "bg-white border-r border-slate-200 text-blue-600 shadow-sm" 
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <Eye size={16} /> Preview
        </button>
        <button
          onClick={() => setView("code")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            view === "code" 
              ? "bg-white border-l border-r border-slate-200 text-blue-600 shadow-sm" 
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <Code size={16} /> Code
        </button>
      </div>

      <LiveProvider code={cleanCode} scope={dynamicScope} noInline={true}>
        {view === "preview" ? (
          <div className="flex-1 bg-white">
            <div className="p-6">
              <LivePreview />
            </div>
            {!isStreaming && (
              <LiveError className="bg-red-50 text-red-600 p-4 font-mono text-xs border-t border-red-200 overflow-x-auto" />
            )}
          </div>
        ) : (
          <div className="flex-1 bg-slate-900 p-6 max-h-[600px] overflow-y-auto">
            <pre className="text-slate-300 font-mono text-sm whitespace-pre-wrap">
              {codeString}
              {isStreaming && <span className="animate-pulse bg-blue-500 text-transparent">_</span>}
            </pre>
          </div>
        )}
      </LiveProvider>

    </div>
  )
}