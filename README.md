---
title: Document AI Analyst
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: Enterprise Agentic RAG — upload PDFs and chat with AI
---

<div align="center">

<br/>

```
██████╗ ██████╗ ███████╗     █████╗ ███████╗███████╗██╗███████╗████████╗ █████╗ ███╗   ██╗████████╗
██╔══██╗██╔══██╗██╔════╝    ██╔══██╗██╔════╝██╔════╝██║██╔════╝╚══██╔══╝██╔══██╗████╗  ██║╚══██╔══╝
██████╔╝██║  ██║█████╗      ███████║███████╗███████╗██║███████╗   ██║   ███████║██╔██╗ ██║   ██║
██╔═══╝ ██║  ██║██╔══╝      ██╔══██║╚════██║╚════██║██║╚════██║   ██║   ██╔══██║██║╚██╗██║   ██║
██║     ██████╔╝██║         ██║  ██║███████║███████║██║███████║   ██║   ██║  ██║██║ ╚████║   ██║
╚═╝     ╚═════╝ ╚═╝         ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝

                        ██████╗  █████╗  ██████╗
                        ██╔══██╗██╔══██╗██╔════╝
                        ██████╔╝███████║██║  ███╗
                        ██╔══██╗██╔══██║██║   ██║
                        ██║  ██║██║  ██║╚██████╔╝
                        ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝
```

### Enterprise Agentic Retrieval-Augmented Generation System

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorDB-FF6B35?style=for-the-badge)](https://trychroma.com/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Inference-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/)
[![Celery](https://img.shields.io/badge/Celery-Redis-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge)](LICENSE)

<br/>

> **Upload · Embed · Retrieve · Chat** — A production-grade AI document assistant built end-to-end with an agentic RAG pipeline, streaming responses, and per-user data isolation.

<br/>

[Features](#-key-features) · [Tech Stack](#-tech-stack) · [Getting Started](#-getting-started) · [Architecture](#-architecture) · [RAG Pipeline](#-rag-pipeline) · [API Reference](#-api-reference) · [Deployment](#-deployment) · [Contributing](#-contributing)

---

</div>

## 🤝 Contributors

Thanks to all the amazing people who have contributed to **PDF-Assistant-RAG**! 🎉

<div align="center">
  <img src="https://contrib.nn.ci/api?repo=param20h/PDF-Assistant-RAG&cols=6" />
</div>
<br/>

> 🌟 **Want to join them?** Check out [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and look for [good first issues](https://github.com/param20h/PDF-Assistant-RAG/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) to get started!

---

<br/>

## 🌟 Overview

**PDF-Assistant-RAG** is a complete, production-ready AI document assistant that lets users upload complex PDFs, financial reports, legal contracts, and research papers — then chat with an AI that provides **accurate, cited answers** powered by a multi-stage Retrieval-Augmented Generation pipeline.

The system uses **hybrid search (vector + BM25) with Reciprocal Rank Fusion** and **cross-encoder reranking** to find the most relevant document chunks, streams AI-generated answers token-by-token, and highlights exact source citations with page numbers — all inside a modern Next.js frontend with JWT-secured per-user data isolation.

<br/>

## 🏗️ Architecture

> Contributor note: see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a route-by-route system map, request-flow diagrams, and Swagger/OpenAPI documentation guidance.

```mermaid
graph TD
    subgraph Frontend["Frontend (Next.js 16)"]
        UI["Dashboard UI (React + Zustand)"]
        Chat["Chat Panel (SSE Streaming)"]
        Viewer["PDF Viewer"]
    end

    subgraph Backend["Backend (FastAPI 0.115+)"]
        API["API Router (/api/v1)"]
        Auth["Auth (JWT + bcrypt)"]
        DB[(PostgreSQL / SQLite)]
        Redis[(Redis)]

        subgraph RAG["RAG Pipeline"]
            Upload["Celery Ingestion Task"]
            Embed["Local Embeddings (all-MiniLM-L6-v2)"]
            EmbedCache["Embedding Cache (Redis + LRU)"]
            BM25["BM25 Index"]
            Retriever["Hybrid Retriever (Vector + BM25 + RRF)"]
            Rerank["Cross-Encoder Reranker (BGE-v2-m3)"]
            Agent["Agent / Generator"]
        end
    end

    subgraph Storage["Storage"]
        Chroma[(ChromaDB)]
        Uploads[("File Storage")]
    end

    subgraph External["External Services"]
        HF["HuggingFace Inference API (Qwen2.5-72B)"]
    end

    UI <-->|REST / Auth| API
    Chat <-->|SSE Streaming| API
    Viewer -->|Serve PDF| API
    API <--> Auth
    API <--> DB
    API --> Upload
    Upload --> Embed
    Embed --> EmbedCache
    Embed -->|Store Vectors| Chroma
    Upload --> BM25
    API <--> Retriever
    Retriever -->|Semantic Search| Chroma
    Retriever -->|Keyword Search| BM25
    Retriever --> Rerank
    Rerank --> Agent
    Agent <-->|LLM Generation| HF
    Upload -->|Store Files| Uploads
    Redis <-->|Task Queue| Upload
```

<br/>

### 🔄 System Flow Overview

1. User uploads a document via the Next.js frontend.
2. FastAPI queues a Celery ingestion task backed by Redis.
3. The worker chunks the document, generates local embeddings (cached via Redis/LRU), builds a BM25 index, and stores vectors in ChromaDB.
4. At query time, hybrid search merges vector and BM25 results via Reciprocal Rank Fusion.
5. A cross-encoder reranker refines the top candidates.
6. The agent assembles a prompt and calls the HuggingFace Inference API.
7. Streamed SSE tokens are returned to the frontend chat panel.

<br/>

## 🛠 Tech Stack

<div align="center">

### Backend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=fastapi" width="30"/> | **FastAPI 0.115+** | Async API framework + SSE streaming |
| <img src="https://skillicons.dev/icons?i=python" width="30"/> | **Python 3.11** | Runtime environment |
| <img src="https://skillicons.dev/icons?i=postgresql" width="30"/> | **PostgreSQL 16 / SQLite** | User accounts & document metadata |
| <img src="https://skillicons.dev/icons?i=redis" width="30"/> | **Redis** | Celery broker, response cache, embedding cache |
| <img src="https://img.shields.io/badge/Celery-37814A?style=flat" height="24"/> | **Celery** | Async document ingestion workers |
| <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat" height="24"/> | **SQLAlchemy** | ORM + migrations |
| <img src="https://img.shields.io/badge/PyJWT-000000?style=flat" height="24"/> | **PyJWT + bcrypt** | JWT authentication |

### Frontend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=nextjs" width="30"/> | **Next.js 16** | React framework (App Router) |
| <img src="https://skillicons.dev/icons?i=react" width="30"/> | **React 19** | UI components |
| <img src="https://skillicons.dev/icons?i=tailwind" width="30"/> | **Tailwind CSS v4** | Utility-first styling |
| <img src="https://img.shields.io/badge/Zustand-000000?style=flat" height="24"/> | **Zustand** | Client state management |
| <img src="https://img.shields.io/badge/shadcn/ui-000000?style=flat" height="24"/> | **shadcn/ui** | Accessible component library |

### AI / ML Pipeline

| | Technology | Purpose |
|---|---|---|
| <img src="https://img.shields.io/badge/all--MiniLM--L6--v2-FFD21E?style=flat" height="24"/> | **all-MiniLM-L6-v2** | Local 384-dim embeddings (no external API) |
| <img src="https://img.shields.io/badge/ChromaDB-FF6B35?style=flat" height="24"/> | **ChromaDB** | Per-user persistent vector collections |
| <img src="https://img.shields.io/badge/rank--bm25-000000?style=flat" height="24"/> | **rank-bm25** | BM25 keyword index per document |
| <img src="https://img.shields.io/badge/RRF-Hybrid_Search-4F46E5?style=flat" height="24"/> | **Reciprocal Rank Fusion** | Merges vector + BM25 rankings |
| <img src="https://img.shields.io/badge/BGE--Reranker--v2--m3-FFD21E?style=flat" height="24"/> | **BGE-Reranker-v2-m3** | Cross-encoder reranking |
| <img src="https://img.shields.io/badge/Qwen2.5--72B-000000?style=flat" height="24"/> | **Qwen2.5-72B-Instruct** | LLM answer generation (HF Inference API) |
| <img src="https://img.shields.io/badge/PyMuPDF-FF0000?style=flat" height="24"/> | **PyMuPDF + pdfplumber + python-docx** | Document text & image extraction |

### DevOps & Tooling

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=docker" width="30"/> | **Docker Multi-Stage** | Containerised deployment |
| <img src="https://skillicons.dev/icons?i=githubactions" width="30"/> | **GitHub Actions** | CI/CD (E2E, security, deploy) |
| <img src="https://img.shields.io/badge/Playwright-45ba4b?style=flat&logo=playwright&logoColor=white" height="24"/> | **Playwright** | E2E + visual regression tests |
| <img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat&logo=prometheus&logoColor=white" height="24"/> | **Prometheus + Grafana** | Metrics & observability |
| <img src="https://img.shields.io/badge/HuggingFace_Spaces-FFD21E?style=flat&logo=huggingface&logoColor=black" height="24"/> | **HuggingFace Spaces** | Production deployment |

</div>

<br/>

## ✨ Key Features

<table>
<tr>
<td width="33%" valign="top">

### 👤 Users
- 🔐 JWT-secured register, login & email verification
- 📄 Upload **PDF**, **DOCX**, **TXT**, and **Markdown**
- 🌐 URL ingestion via web crawler
- 💬 Ask questions in natural language
- 🌊 **Streaming AI responses** token-by-token
- 📚 Inline **source citations** with page numbers
- 📥 Export chat as **Markdown, TXT, or PDF**
- 🗂️ Per-user complete data isolation

</td>
<td width="33%" valign="top">

### 🤖 RAG Pipeline
- 🔪 Smart **recursive text chunking** (configurable size & overlap)
- 🧠 **Local embeddings** — no data leaves your machine
- ⚡ **Embedding cache** (Redis + LRU) — skip redundant computation
- 🔍 **Hybrid search** — vector + BM25 merged via RRF
- 🏆 **Cross-encoder reranking** for precision answers
- 🖼️ **Image caption extraction** from PDF figures
- 🔗 **URL extraction** from PDF link annotations
- 🗺️ **Knowledge graph** (GraphRAG) per document

</td>
<td width="33%" valign="top">

### ⚙️ Engineering
- 🚀 **Async FastAPI** with SSE streaming
- 🗄️ **PostgreSQL** metadata + **ChromaDB** vectors
- 🔄 **Celery + Redis** async ingestion pipeline
- 🐳 **Multi-stage Docker** with CPU & GPU profiles
- 📊 **Prometheus metrics** + Grafana dashboard
- 🩺 **Deep health endpoint** — DB, Redis, Celery, ChromaDB
- 🔒 Rate limiting, CORS, file validation, JWT expiry
- 🧪 **Playwright** E2E + visual regression tests

</td>
</tr>
</table>

<br/>

## 📁 Project Structure

```
PDF-Assistant-RAG/
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app — lifespan, middleware, routers
│   │   ├── config.py               # Pydantic settings (env vars)
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── database.py             # Engine, session, migrations
│   │   ├── auth.py                 # JWT helpers
│   │   ├── tasks.py                # Celery task definitions
│   │   │
│   │   ├── routes/
│   │   │   ├── auth.py             # Register, login, OAuth
│   │   │   ├── documents.py        # Upload, list, delete, status
│   │   │   ├── chat.py             # Ask, stream, history, export
│   │   │   ├── health.py           # Deep health check endpoint
│   │   │   ├── admin.py            # Admin stats
│   │   │   └── workspaces.py       # Workspace management
│   │   │
│   │   ├── rag/
│   │   │   ├── chunker.py          # PDF/DOCX/TXT extraction + chunking
│   │   │   ├── embeddings.py       # Local embeddings + Redis/LRU cache
│   │   │   ├── vectorstore.py      # ChromaDB operations
│   │   │   ├── bm25.py             # BM25 index per document
│   │   │   ├── retriever.py        # Hybrid search + RRF + reranking
│   │   │   ├── reranker.py         # Cross-encoder reranker
│   │   │   ├── vision.py           # Image caption extraction
│   │   │   ├── url_extractor.py    # PDF URL/link extraction
│   │   │   ├── graph_builder.py    # Knowledge graph (GraphRAG)
│   │   │   ├── agent.py            # LLM answer generation
│   │   │   └── summarizer.py       # Document summarisation
│   │   │
│   │   └── services/
│   │       └── document_ingestion.py  # End-to-end ingestion pipeline
│   │
│   ├── tests/                      # pytest test suite
│   ├── requirements.txt
│   └── migrate_add_extracted_urls.py
│
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router pages
│   │   ├── components/             # React components
│   │   ├── store/                  # Zustand state stores
│   │   ├── lib/                    # API client, auth, utilities
│   │   └── services/               # API service layer
│   ├── e2e/                        # Playwright E2E + snapshot tests
│   ├── next.config.ts
│   └── playwright.config.ts
│
├── docs/
│   └── ARCHITECTURE.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Backend CI
│       ├── e2e.yml                 # Playwright E2E + visual regression
│       ├── deploy.yml              # Docker build (main branch)
│       └── devsecops.yml           # Security scans
│
├── docker-compose.yml              # CPU + GPU + debug profiles + log rotation
├── Dockerfile                      # Multi-stage backend build
├── frontend/Dockerfile             # Multi-stage frontend build (nginx)
└── .env.example
```

<br/>

## 🚀 Getting Started

### Prerequisites

- ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white) **Python 3.11+**
- ![Node](https://img.shields.io/badge/Node.js-20+-339933?style=flat&logo=nodedotjs&logoColor=white) **Node.js 20+**
- ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white) **Docker + Docker Compose** (recommended)
- ![HuggingFace](https://img.shields.io/badge/HuggingFace_Token-FFD21E?style=flat&logo=huggingface&logoColor=black) **HuggingFace API token** — [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (free)

---

### 1. Clone the Repository

```bash
git clone https://github.com/param20h/PDF-Assistant-RAG.git
cd PDF-Assistant-RAG
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-strong-random-secret
DATABASE_URL=postgresql://pdf_rag_user:pdf_rag_pass@localhost:5432/pdf_rag
HF_TOKEN=hf_your_huggingface_token_here
UPLOAD_DIR=./data/uploads
CHROMA_PERSIST_DIR=./data/chroma_db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

> Get your free HuggingFace token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

#### Email Verification Setup (optional)

```env
FRONTEND_URL=http://localhost:3000
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_or_gmail_app_password
MAIL_FROM=your_sender_email@example.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

Without SMTP settings, registration returns a local verification link so contributors can test without email credentials.

### 3. Run with Docker (recommended)

```bash
# CPU-only (no GPU needed)
docker compose --profile cpu up --build

# GPU-accelerated (requires NVIDIA Container Toolkit)
docker compose --profile gpu up --build

# Also start pgAdmin at http://localhost:5050
docker compose --profile cpu --profile debug up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:7860 |
| API Docs | http://localhost:7860/docs |
| pgAdmin | http://localhost:5050 (debug profile) |

### 4. Run Locally (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860

# Celery worker (separate terminal)
celery -A app.celery_app.celery_app worker --loglevel=info

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 5. Set up crawl4ai (URL Upload Feature — optional)

```bash
crawl4ai-setup
```

<br/>

## 🧠 RAG Pipeline

```
                    ┌─────────────────────────────────────────────┐
                    │         PDF / DOCX / TXT / MD Upload        │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   PyMuPDF / pdfplumber / python-docx Parser │
                    │   + Image caption extraction                │
                    │   + PDF URL/link annotation extraction      │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │      Recursive Character Text Splitter      │
                    │   chunk_size=1000  |  overlap=200           │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │  all-MiniLM-L6-v2  (local embeddings)       │
                    │  384-dim · Redis + LRU cache (24h TTL)      │
                    └──────────────┬──────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
         ┌──────────────────┐         ┌─────────────────────┐
         │ ChromaDB vectors │         │  BM25 keyword index │
         │ (per-user coll.) │         │  (per-document .pkl)│
         └──────────────────┘         └─────────────────────┘

                          ── At Query Time ──

  User Question ──▶ Embed (cached) ──▶ Vector Search (Top-K=20)
                         │
                         ├──▶ BM25 Search (Top-K=20)
                         │
                         ▼
              Reciprocal Rank Fusion (RRF, k=60)
                         │
                         ▼
          BGE-Reranker-v2-m3 Cross-Encoder (Top-K=8)
                         │
                         ▼
        Prompt Assembly (system + context + question)
                         │
                         ▼
        Qwen2.5-72B-Instruct (HF Inference API)
                         │
                         ▼
        Streamed SSE tokens ──▶ Frontend ChatPanel
```

<br/>

## 📡 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/register` | ❌ | Create a new user account |
| `POST` | `/api/v1/auth/login` | ❌ | Login and receive JWT tokens |
| `GET` | `/api/v1/auth/me` | ✅ | Get current user profile |
| `POST` | `/api/v1/documents/upload` | ✅ | Upload PDF/DOCX/TXT and enqueue ingestion (`202`) |
| `POST` | `/api/v1/documents/urlupload` | ✅ | Crawl a URL and ingest as document |
| `GET` | `/api/v1/documents/` | ✅ | List documents (pagination + `?q=` name filter) |
| `GET` | `/api/v1/documents/{id}` | ✅ | Get document metadata (incl. extracted URLs) |
| `GET` | `/api/v1/documents/{id}/status` | ✅ | Poll ingestion progress |
| `DELETE` | `/api/v1/documents/{id}` | ✅ | Soft-delete document |
| `POST` | `/api/v1/chat/ask/stream` | ✅ | Ask a question (SSE streaming) |
| `GET` | `/api/v1/chat/history/{doc_id}` | ✅ | Get chat history for a document |
| `DELETE` | `/api/v1/chat/history/{doc_id}` | ✅ | Clear chat history |
| `GET` | `/api/v1/chat/export/{doc_id}` | ✅ | Export transcript as MD / TXT / PDF |
| `GET` | `/api/v1/chat/sessions` | ✅ | List chat sessions |
| `POST` | `/api/v1/chat/sessions` | ✅ | Create chat session |
| `GET` | `/api/v1/health/status` | ❌ | Deep health check (DB, Redis, Celery, ChromaDB) |
| `GET` | `/api/health` | ❌ | Basic liveness check |

> Full interactive docs at `/docs` (Swagger UI) when running locally.

<br/>

## 📦 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | JWT signing secret. Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `HF_TOKEN` | ✅ | — | HuggingFace API token for LLM inference |
| `DATABASE_URL` | ❌ | `sqlite:///./data/app.db` | SQLAlchemy connection string (SQLite or PostgreSQL) |
| `CELERY_BROKER_URL` | ❌ | `redis://localhost:6379/0` | Redis broker for Celery |
| `CELERY_RESULT_BACKEND` | ❌ | `redis://localhost:6379/1` | Redis backend for Celery results |
| `REDIS_URL` | ❌ | — | Redis URL for response + embedding cache |
| `UPLOAD_DIR` | ❌ | `./data/uploads` | File storage directory |
| `CHROMA_PERSIST_DIR` | ❌ | `./data/chroma_db` | ChromaDB persistence directory |
| `EMBEDDING_MODEL` | ❌ | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `EMBEDDING_CACHE_TTL` | ❌ | `86400` | Embedding cache TTL in seconds (24h) |
| `LLM_MODEL` | ❌ | `Qwen/Qwen2.5-72B-Instruct` | HuggingFace model for answer generation |
| `LLM_TEMPERATURE` | ❌ | `0.3` | LLM sampling temperature |
| `RERANKER_MODEL` | ❌ | `BAAI/bge-reranker-v2-m3` | Cross-encoder reranker model |
| `USE_HYBRID_SEARCH` | ❌ | `True` | Enable BM25 + vector hybrid search |
| `RRF_K` | ❌ | `60` | RRF smoothing constant |
| `CHUNK_SIZE` | ❌ | `1000` | Characters per document chunk |
| `CHUNK_OVERLAP` | ❌ | `200` | Overlap between consecutive chunks |
| `TOP_K_RETRIEVAL` | ❌ | `20` | Candidates retrieved from vector store |
| `TOP_K_RERANK` | ❌ | `8` | Final chunks after reranking |
| `VISION_PROVIDER` | ❌ | — | Set to `openai` to use GPT-4o-mini for image captions |
| `OPENAI_API_KEY` | ❌ | — | Required when `VISION_PROVIDER=openai` |
| `ENVIRONMENT` | ❌ | `development` | Set to `production` to lock CORS |
| `FRONTEND_URL` | ❌ | `http://localhost:3000` | Public frontend URL for OAuth + email links |
| `NEXT_PUBLIC_API_URL` | ❌ | `http://localhost:7860` | Backend URL injected at frontend build time |

<br/>

## 📜 Scripts

### Backend (`backend/`)

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start FastAPI with hot reload |
| `celery -A app.celery_app.celery_app worker --loglevel=info` | Start Celery worker |
| `python migrate_add_extracted_urls.py` | Run URL extraction column migration |
| `python scripts/run_ragas_eval.py --user-id <id>` | Run RAGAS evaluation (vector vs GraphRAG) |

### Frontend (`frontend/`)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Next.js dev server |
| `npm run build` | Production build |
| `npm run test` | Run Vitest unit tests |
| `npm run test:e2e` | Run Playwright E2E tests |
| `npx playwright test e2e/snapshots.spec.ts --update-snapshots` | Regenerate visual regression baselines |

### Docker

| Command | Description |
|---------|-------------|
| `docker compose --profile cpu up --build` | Full stack — CPU only |
| `docker compose --profile gpu up --build` | Full stack — GPU accelerated |
| `docker compose --profile debug up` | Also start pgAdmin at http://localhost:5050 |
| `docker compose down` | Stop all containers |

> **GPU profile** requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

<br/>

## 🌐 Deployment

### HuggingFace Spaces

1. Fork this repo and create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) (SDK: Docker)
2. Set Space secrets: `HF_TOKEN`, `SECRET_KEY`, `DATABASE_URL`
3. Push to the `hf` remote:

```bash
git remote add hf https://<username>:<HF_TOKEN>@huggingface.co/spaces/<username>/<space-name>
git push hf main
```

### Self-Hosted / VPS

```bash
docker compose --profile cpu up -d --build
# App at http://your-server:7860
# Frontend at http://your-server:3000
```

<br/>

## 🤝 Contributing

This project is participating in **GirlScript Summer of Code**! We welcome contributors of all skill levels.

**Branch Strategy:**

| Branch | Purpose |
|--------|---------|
| `main` | Production — HuggingFace deployed (admin only) |
| `dev` | All contributor PRs target here |
| `feature/*` / `fix/*` / `docs/*` | Your working branches |

```bash
# Always branch from dev
git checkout -b feature/my-feature upstream/dev
```

**Quick links:**
- 📋 [Good First Issues](https://github.com/param20h/PDF-Assistant-RAG/issues?q=label%3A%22good+first+issue%22)
- 📖 [Contributing Guide](CONTRIBUTING.md)
- 💬 [Discussions](https://github.com/param20h/PDF-Assistant-RAG/discussions)

<br/>

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](license) for more information.

---

<div align="center">

<br/>

**Built with 💙 by the open-source community**

*If you found this project helpful, please give it a ⭐ — it helps contributors discover it!*

<br/>

[![Stack](https://skillicons.dev/icons?i=fastapi,python,react,nextjs,docker)](https://skillicons.dev)

<br/>

**[⬆ Back to top](#)**

</div>
