# Job Search MCP

An agentic job intelligence platform that combines MCP, RAG, and multi-source job retrieval to help users find relevant roles, compare matches against a resume, and identify useful signals like visa sponsorship.

## Overview

The goal of this project is to build a practical AI workflow, not just a chatbot. It focuses on:

- collecting jobs from multiple sources
- indexing and searching jobs with retrieval
- matching resumes against jobs
- using agents to route work through specialized steps
- exposing actions through MCP tools

## Why This Project Matters

This project is designed to demonstrate:

- AI engineering
- agent workflows
- MCP integration
- RAG pipelines
- scraping and API integration
- embeddings and search
- backend engineering
- production-minded design

It is meant to be a strong portfolio project because it solves a real workflow and shows modern AI system design.

## Planned Features

### MVP

- multi-source job ingestion
- resume parsing and skill extraction
- ATS-style resume scoring
- job-to-resume match scoring
- RAG-powered search over indexed jobs
- visa sponsorship detection
- agent-based workflow orchestration

### MCP Tools

Planned tools include:

- `search_jobs()`
- `analyze_resume()`
- `match_resume_to_job()`
- `find_sponsorship_jobs()`
- `generate_cover_letter()`

The current implementation exposes these capabilities through the service layer and API endpoints, with an MCP-style tool facade in the codebase.

### MCP Server

The project also includes a real MCP server entrypoint that exposes the same search and resume tools over the Model Context Protocol.

Run it with:

- `uv run job-search-mcp mcp`

This uses the `mcp` Python package and communicates over stdio, which is the common transport for local MCP clients.

### Resume Upload

The first implementation supports uploading a text-based resume file through:

- `POST /resumes/upload`

That endpoint extracts text, runs resume analysis, and returns the parsed result.

### Ingestion

The project now includes a pluggable ingestion layer with demo adapters for:

- Jsearch
- Greenhouse
- Lever

You can seed the repository through `POST /ingestion/all` or ingest a single source through `POST /ingestion/{source}`.

For explicit imports, use:

- `POST /ingestion/import`

That endpoint accepts a source plus a board/company reference. For example, it can ingest a Greenhouse board slug or a Lever company slug directly.

### Background Sync

Configured sources can refresh automatically in the background when `BACKGROUND_SYNC_ENABLED=true`.
You can inspect or trigger it through:

- `GET /ingestion/sync/status`
- `POST /ingestion/sync/run`

### Persistence

Jobs are now stored in a local SQLite database instead of only living in memory.
The default path is `./job_search_mcp.db`, configured through `DATABASE_URL`.

### Semantic Search

Search now uses keyword scoring plus vector embeddings. By default it uses an in-memory Qdrant-backed index for development and can switch to a real Qdrant instance through `QDRANT_URL` and `QDRANT_COLLECTION`.

### LLM Support

If `OPENAI_API_KEY` is set, cover letters are generated through the OpenAI API.
If no key is present, the app falls back to a deterministic local template.

### Frontend

The root route now redirects to the React app by default, and the React app provides:

- job search
- resume upload or text analysis
- ingestion refresh
- cover-letter generation

There is also a separate React app in `frontend/` for a richer browser interface.

## Suggested Architecture

The intended system is split into a few layers:

- ingestion layer for collecting job data from sources like Jsearch, Greenhouse, Lever, Adzuna, and RemoteOK
- retrieval layer for indexing jobs and supporting semantic search
- agent layer for planning, matching, and response generation
- MCP layer for exposing capabilities as tools
- frontend layer for user interaction and job exploration

## Project Structure

The current codebase is organized as:

```text
job_search_mcp/
|-- main.py              # Simple entrypoint for local runs
|-- README.md            # Project overview and setup
|-- PROJECT.md           # Longer planning notes
|-- pyproject.toml       # Python package metadata and dependencies
|-- frontend/           # React UI
|-- tests/
|   |-- test_api.py      # API smoke tests
|   `-- test_core.py     # Core behavior tests
`-- job_search_mcp/
    |-- __init__.py      # Package metadata
    |-- api.py           # FastAPI application skeleton
    |-- embeddings.py    # Local text embedding helpers
    |-- cli.py           # Command-line entrypoint
    |-- frontend.py      # Browser UI HTML
    |-- llm.py           # Cover-letter generation
    |-- models.py        # Shared data models
    |-- settings.py      # Environment configuration
    |-- storage.py       # SQLite persistence
    |-- vector_index.py  # Qdrant-backed vector index
    `-- services/
        |-- __init__.py
        |-- ingestion.py # Job ingestion service
        |-- jobs.py      # Job repository and search logic
        |-- mcp_tools.py # MCP-style tool facade
        `-- sources.py   # Demo source adapters
```

## Recommended Stack

- Python
- FastAPI
- OpenAI API
- LangGraph or OpenAI Agents SDK
- Qdrant or pgvector
- Next.js
- Tailwind
- PyMuPDF, Docling, or Unstructured for parsing
- PyMuPDF and python-docx for document parsing support

## Project Positioning

A stronger name and framing for the project is:

> Agentic Job Intelligence Platform with MCP + RAG

That framing communicates the system design more clearly than a generic "AI job bot."

## Development Roadmap

### Phase 1: Foundation

- job ingestion
- embeddings
- vector database setup
- basic search
- repository model for jobs
- CLI and API skeleton

### Phase 2: Core Intelligence

- agent workflows
- MCP tools
- resume analysis
- job ranking logic
- resume matching logic

### Phase 3: Product Layer

- frontend
- deployment
- observability
- polish
- streaming responses
- tool traces and logging

## Good Demo Features

These are useful if you want the project to feel production-ready:

- streaming responses
- tool traces
- agent visualization
- structured JSON outputs
- logging and latency metrics

## Repository Status

The repository is currently in early development. The main focus is to define the project clearly before building the full system.

## Setup

### Prerequisites

- Python 3.12 or newer
- `uv` if you want fast local environment management
- Copy `.env.example` to `.env` and fill in the values when you connect external services

### Install

From the project root:

```bash
uv sync
```

If you are not using `uv`, you can still run the project directly with Python once dependencies are added.

### Run

The current entrypoint is:

```bash
python main.py
```

If you are using `uv`:

```bash
uv run python main.py
```

To run the CLI entrypoint directly after installation:

```bash
uv run job-search-mcp
```

To see the seeded demo jobs:

```bash
uv run job-search-mcp demo
```

If `uv run` has cache permission issues on your machine, use:

```bash
python main.py demo
```

To start the API server during development:

```bash
uv run uvicorn job_search_mcp.api:app --reload
```

### Development Loop

When you start building the actual app, a good workflow will be:

1. add dependencies to `pyproject.toml`
2. implement the ingestion and retrieval modules
3. expose API or MCP tools
4. connect the frontend
5. add tests and observability

### Frontend Dev

From `frontend/`:

```bash
npm install
npm run dev
```

## Next Step

Build the first MVP around:

1. job ingestion
2. semantic indexing
3. search and ranking
4. resume matching
