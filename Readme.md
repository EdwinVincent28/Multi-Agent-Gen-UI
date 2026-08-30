# Multi-Agent Gen-UI

> A self-correcting AI pipeline that turns a data source — CSV upload or a live Twitch channel — into deployed, production-ready React dashboards, autonomously.

## Overview

Multi-Agent Gen-UI is an advanced cognitive architecture built on LangGraph that ingests a dataset, cleans and analyzes it, synthesizes a fully functional React dashboard, and streams the result to the client in real time over WebSockets.

Two data sources are supported: an uploaded CSV, or a **live Twitch channel** (real-time viewer count, chat activity, top emotes), which the swarm treats identically once ingested — the same agents generate the dashboard either way.

An optional wireframe image can be uploaded alongside either source. A **Vision Analyst** agent extracts the exact grid structure, component types, and data mapping from the sketch, so the generated dashboard follows your intended layout instead of a generic one.

To ensure production-grade reliability, the pipeline includes an **LLM-as-a-Judge quality gate**: a lightweight evaluator model reviews each generated component against strict UI and data constraints. If it detects a hallucinated charting library or syntax error, it intercepts the code and triggers an automatic retry loop (bounded to 3 attempts) rather than shipping broken components to the client. Every agent logs its own latency, token usage, and output individually — not just an aggregate — so a slow or expensive step is identifiable directly from the logs.

## Core Architecture & Features

- **Multi-Agent Reasoning Pipeline:** Orchestrated with LangGraph, using specialized nodes (Data Engineer, Analyst, Vision Analyst, Frontend Engineer, Evaluator) to handle specific tasks instead of relying on one monolithic prompt.
- **Live Twitch Data Source:** An anonymous IRC-over-WebSocket chat listener and Helix API viewer-count polling feed a sliding-window aggregator, producing periodic snapshot rows the swarm consumes exactly like CSV rows — no changes needed downstream. The entry router detects a pre-shaped Twitch source and skips CSV parsing accordingly.
- **RAG-Based "Ask Your Dashboard" Q&A:** For live Twitch sessions, a background indexer batches viewer/chat statistics and filtered chat excerpts every 5 minutes, embeds them locally (no external API), and stores them in Qdrant scoped to that one session. A chat widget lets you ask questions about the stream so far ("why did viewers spike just now?"), answered by retrieving the relevant indexed context and generating a grounded response.
- **Wireframe-to-Blueprint Vision Analyst:** Upload a reference image; the agent identifies each component's type and what data it should represent (not just "there's a chart here"), which the Frontend Engineer follows as an explicit checklist rather than a loose suggestion.
- **Self-Correction Quality Gate:** An Evaluator node checks generated code against explicit framework constraints (shadcn/ui component rules, Recharts-only charting, real dataset schema) and routes failures back to the Frontend Engineer for a bounded maximum of 3 retries.
- **Per-Node Telemetry & Observability:** Every agent — not just the pipeline as a whole — logs its own latency, token usage, and a truncated preview of its actual output via `loguru`, at DEBUG level for response bodies. Redis persists session state and checkpoints across the swarm's execution.
- **Optimized Build & Deployment Pipeline:** Drastically reduced cloud deployment build times by maintaining a pre-scaffolded Vite + Tailwind + shadcn/ui dashboard template with pre-installed npm dependencies, decoupling heavy compilation from the real-time generation loop. **Known limitation:** a deployed dashboard is a snapshot from the moment of deployment — live Twitch updates continue only in the active browser session against the running backend, not in the deployed Cloud Run instance.
- **Live Streaming Dual-Pane UI:** Both first-time generation and edits stream over native WebSockets — per-node status updates ("Analyzing trends...", "Writing your dashboard code...") followed by the generated React code character-by-character, into a Code/Preview interface that switches to a live `react-live` sandbox once generation completes.
- **Human-in-the-Loop Cloud Deployment:** An isolated Model Context Protocol (MCP) server containerizes the scaffolded dashboard and deploys it to Google Cloud Run — decoupled from the main backend so deployment can be audited and triggered independently.

![Architecture Diagram](./assets/architecture.png)

## Tech Stack

- **Backend:** Python, FastAPI, LangGraph, Google Gemini (LLM inference + vision), Loguru (Structured Logging), Redis (State Checkpointing), Qdrant + FastEmbed (session-scoped RAG memory, local embeddings), SQLAlchemy (PostgreSQL)
- **Live Data:** Twitch Helix API (viewer count), Twitch IRC over WebSocket (anonymous chat listener), Pillow (wireframe image compression)
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts, react-live
- **Deployment:** Docker, Google Cloud Run, Cloud Build

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── llm.py            # Gemini client factory, shared response-parsing helpers
│   │   │   ├── telemetry.py      # Shared per-node latency/token/response logging
│   │   │   └── ...                # Config, thread_id helpers
│   │   ├── mcp_server/           # MCP server for GCP dashboard deployment
│   │   ├── models/               # DB + Pydantic schemas
│   │   ├── routers/              # FastAPI route definitions (generate, twitch, chat, auth)
│   │   ├── services/
│   │   │   ├── twitch_service.py       # Helix API auth + viewer count
│   │   │   ├── twitch_listener.py      # Anonymous IRC chat listener
│   │   │   ├── twitch_data_adapter.py  # Sliding-window stats aggregation
│   │   │   ├── twitch_session.py       # Live session orchestration + RAG indexing
│   │   │   ├── twitch_qa_service.py    # RAG retrieval + grounded Q&A generation
│   │   │   └── memory_service.py       # Qdrant/embeddings — session-scoped Twitch context
│   │   └── swarm/                # LangGraph multi-agent implementation
│   │       ├── agents/           # Data Engineer, Analyst, Vision Analyst, Frontend Engineer, Evaluator
│   │       ├── graph.py          # Graph definition and routing (CSV / Twitch / edit entry points)
│   │       └── state.py          # Shared graph state schema
│   ├── dashboard_template/       # Pre-scaffolded Vite+Tailwind template for fast cloud builds
│   ├── logs/                     # Telemetry and execution log outputs
│   ├── main.py                   # FastAPI entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/           # SandboxRenderer and shared UI
│   │   ├── pages/                # Dashboard (CSV/Twitch toggle + Q&A widget), Login, Register
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml             # Local Redis / Qdrant / Postgres orchestration
└── .env.example
```

## Quickstart & Local Setup

### 1. Prerequisites

- Docker Desktop
- Python 3.10+
- Node.js 18+
- **Google Gemini API key** (free tier) — required for all LLM inference and wireframe analysis
- **Twitch application credentials** (free, from [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps)) — required only for the live Twitch data source and Q&A features
- **Google Cloud Platform (GCP) Account** — required only for the Cloud Run deployment feature

### 2. Environment Variables

Copy `.env.example` to `.env` in the project root and fill in your values.

```
GEMINI_API_KEY=your_gemini_api_key_here
# Optional overrides — sensible defaults are used if omitted:
# GEMINI_TEXT_MODEL=gemini-3.6-flash
# GEMINI_VISION_MODEL=gemini-3.6-flash

TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
# Optional — lowers the RAG indexing interval for local testing (default 300s):
# TWITCH_INDEXING_INTERVAL_SECONDS=300

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

The application will now be running at `http://localhost:5173`. Check the backend terminal during generation to view per-node latency, token, and response telemetry.

## Roadmap (Future Scope)

- [ ] **User Preference Memory (RAG for UI Tastes):** A structured (not vector-search-based) per-user preference store — e.g. theme, chart style — looked up by user ID at generation time. An earlier vector-similarity approach to this was built, found to cause a real bug (silently overwriting live edits with unrelated past dashboards), and removed; a structured lookup avoids that failure mode entirely.
- [ ] **Live Data for Deployed Dashboards:** Currently, a deployed Cloud Run dashboard is a static snapshot. Extending live updates to deployed instances requires either the deployed app maintaining its own connection back to a *hosted* backend, or (for chat specifically) connecting directly to Twitch from the browser — both undeployed pending backend hosting.
- [ ] **Agentic Code Interpreter for the Analyst:** Equip the Analyst node with a Python REPL sandbox to execute actual Pandas code for mathematically verified insights instead of relying on standard LLM inference.
- [ ] **Live Database Connectors via MCP:** Build standard MCP tools to query live production databases (MySQL/MongoDB), following the same pattern proven out for the Twitch live-data integration.
- [ ] **"Eject to Local" Export Feature:** Package generated React components into a boilerplate Vite scaffolding zip for immediate local developer handoff.

## About

Built to explore advanced AI system design — multi-agent orchestration, self-correction loops, live data ingestion, retrieval-augmented generation, and real-time LLM-to-UI pipelines.

[LinkedIn](https://linkedin.com/in/edwin-vincent-evt) · [GitHub](https://github.com/EdwinVincent28)