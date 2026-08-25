import React, { useState, useMemo, useEffect, useRef } from "react"
import { LiveProvider, LiveError, LivePreview } from "react-live"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import * as LucideIcons from "lucide-react"
import { Eye, Code } from "lucide-react"
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts"
import clsx from "clsx"
import { motion, AnimatePresence } from "framer-motion"

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
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  clsx,
  motion,
  AnimatePresence,
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
  const codeContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isStreaming) {
      setView("code")
    } else {
      const timer = setTimeout(() => setView("preview"), 300)
      return () => clearTimeout(timer)
    }
  }, [isStreaming])

  useEffect(() => {
    if (codeContainerRef.current) {
      codeContainerRef.current.scrollTop = codeContainerRef.current.scrollHeight
    }
  }, [codeString])

  const cleanCode = useMemo(() => {
    if (!codeString) return ""

    let processed = codeString
      .replace(/```[a-zA-Z]*\n?/g, "")
      .replace(/```/g, "")
      .trim()

    processed = processed
      .replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];?/g, "")
      .replace(/import\s+['"][^'"]+['"];?/g, "")
      .trim()

    let componentName = "Dashboard" 

    const inlineFnMatch = processed.match(/export\s+default\s+function\s+(\w+)/)
    if (inlineFnMatch) {
      componentName = inlineFnMatch[1]
      processed = processed.replace(/export\s+default\s+(?=function\s+\w+)/, "")
    } else {

      const refMatch = processed.match(/export\s+default\s+(\w+)\s*;?/)
      if (refMatch) {
        componentName = refMatch[1]
        processed = processed.replace(/export\s+default\s+\w+\s*;?/, "")
      } else {
        processed = processed.replace(/export\s+default\s+/, "")
        const fnDeclMatch = processed.match(/function\s+(\w+)\s*\(/)
        const constDeclMatch = processed.match(/const\s+(\w+)\s*(?::[^=]+)?=\s*\(?[^=]*=>/)
        if (fnDeclMatch) componentName = fnDeclMatch[1]
        else if (constDeclMatch) componentName = constDeclMatch[1]
      }
    }

    processed += `\n\nrender(<${componentName} />);`

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
          <div ref={codeContainerRef} className="flex-1 bg-slate-900 p-6 max-h-[600px] overflow-y-auto">
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