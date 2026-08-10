# Multi-Agent Gen-UI

> A self-correcting AI pipeline that turns raw CSV/JSON data into deployed, production-ready React dashboards — autonomously.

## Overview

Multi-Agent Gen-UI is an advanced cognitive architecture built on LangGraph that ingests a raw dataset, cleans and analyzes it, synthesizes a fully functional React dashboard, and streams the result to the client in real time over WebSockets.

To ensure production-grade reliability, the pipeline includes an **LLM-as-a-Judge quality gate**: a lightweight evaluator model reviews each generated component against strict UI and data constraints. If it detects a hallucinated charting library or syntax error, it intercepts the code and triggers an automatic retry loop rather than shipping broken components to the client. The entire execution is continuously monitored via structured logging to track token overhead and system latency.

## Core Architecture & Features

- **Multi-Agent Reasoning Pipeline:** Orchestrated with LangGraph, using specialized nodes (Data Engineer, Analyst, Frontend Engineer, Evaluator) to handle specific tasks instead of relying on one monolithic prompt.
- **Self-Correction Quality Gate:** An Evaluator node checks generated code against explicit framework constraints (shadcn/ui component rules, Recharts-only charting, real dataset schema) and routes failures back to the Frontend Engineer for a bounded maximum of 3 retries.
- **End-to-End Telemetry & Observability:** Integrated `loguru` and Redis to capture and write execution metrics, continuously benchmarking generation latency, token consumption, and the exact overhead cost of the retry loops.
- **Optimized Build & Deployment Pipeline:** Drastically reduced cloud deployment build times by maintaining a pre-scaffolded Vite + Tailwind + shadcn/ui dashboard template with pre-installed npm dependencies, decoupling heavy compilation from the real-time generation loop.
- **Live Streaming Dual-Pane UI:** LLM-generated React code streams character-by-character over native WebSockets into a Code/Preview interface, switching to a live `react-live` sandbox preview once generation completes.
- **Semantic UI Memory:** Qdrant vector search allows the system to recall and reuse previously generated, user-preferred UI patterns for similar datasets or prompts.
- **Human-in-the-Loop Cloud Deployment:** An isolated Model Context Protocol (MCP) server containerizes the scaffolded dashboard and deploys it to Google Cloud Run — decoupled from the main backend so deployment can be audited and triggered independently.

## Tech Stack

- **Backend:** Python, FastAPI, LangGraph, Loguru (Structured Logging), Redis (State Checkpointing), Qdrant (Vector Memory), SQLAlchemy (PostgreSQL)
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts, react-live
- **Deployment:** Docker, Google Cloud Run, Cloud Build

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── core/             # Config, LLM client, thread_id helpers
│   │   ├── mcp_server/       # MCP server for GCP dashboard deployment
│   │   ├── models/           # DB + Pydantic schemas
│   │   ├── routers/          # FastAPI route definitions (generate, chat, auth)
│   │   ├── services/         # Swarm invocation, memory, auth services
│   │   └── swarm/            # LangGraph multi-agent implementation
│   │       ├── agents/       # Data Engineer, Analyst, Frontend Engineer, Evaluator
│   │       ├── graph.py      # Graph definition and routing
│   │       └── state.py      # Shared graph state schema
│   ├── dashboard_template/   # Pre-scaffolded Vite+Tailwind template for fast cloud builds
│   ├── logs/                 # Telemetry and execution log outputs
│   ├── main.py               # FastAPI entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # SandboxRenderer and shared UI
│   │   ├── pages/            # Dashboard, Login, Register
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml        # Local Redis / Qdrant / Postgres orchestration
└── .env.example
```

## Quickstart & Local Setup

### 1. Prerequisites

- Docker Desktop
- Python 3.10+
- Node.js 18+

### 2. Environment Variables

Copy `.env.example` to `.env` in the project root and fill in your values. You will need a free Groq API key to run the LLM inference.

```
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=your_secure_jwt_secret
JWT_ALGORITHM="HS256"
POSTGRES_URL="postgresql://admin:adminpassword@localhost:5432/swarm_db"
REDIS_URL="redis://localhost:6379/0"
QDRANT_URL="http://localhost:6333"
```

### 3. Start Infrastructure

Spin up the Redis, Qdrant, and PostgreSQL containers:

```bash
docker-compose up -d
```

### 4. Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Setup Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The application will now be running at `http://localhost:5173`. Check the backend terminal during generation to view real-time latency and token telemetry logs.

## Roadmap (Future Scope)

- [ ] **User Preference Memory (RAG for UI Tastes):** Extract and embed user stylistic preferences (e.g., "dark mode", "always use line charts") into Qdrant to dynamically inject into future system prompts.
- [ ] **Agentic Code Interpreter for the Analyst:** Equip the Analyst node with a Python REPL sandbox to execute actual Pandas code for mathematically verified insights instead of relying on standard LLM inference.
- [ ] **Live Database Connectors via MCP:** Build standard MCP tools to query live production databases (MySQL/MongoDB) instead of relying solely on CSV file uploads.
- [ ] **"Eject to Local" Export Feature:** Package generated React components into a boilerplate Vite scaffolding zip for immediate local developer handoff.

## About

Built to explore advanced AI system design — multi-agent orchestration, self-correction loops, semantic memory, and real-time LLM-to-UI pipelines.

[LinkedIn](https://linkedin.com/in/edwin-vincent-evt) · [GitHub](https://github.com/EdwinVincent28)