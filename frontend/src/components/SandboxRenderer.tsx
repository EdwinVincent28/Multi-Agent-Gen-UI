import React, { useState, useMemo } from "react"
import { LiveProvider, LiveError, LivePreview } from "react-live"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import * as LucideIcons from "lucide-react"

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
}

export default function SandboxRenderer({ codeString, data }: { codeString: string, data: any[] | null }) {
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
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
      <LiveProvider code={cleanCode} scope={dynamicScope} noInline={true}>
        <div className="p-6">
          <LivePreview />
        </div>
        <LiveError className="bg-red-900 text-red-100 p-4 font-mono text-sm overflow-x-auto" />
      </LiveProvider>
    </div>
  )
}