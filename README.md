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
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-FF6B35?style=for-the-badge)](https://trychroma.com/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Inference-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/)
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


### 📋 Contributions

<div align="center">

| Avatar | Contributor | Role | Key Contributions |
|:------:|:-----------:|:----:|:-----------------|
| <img src="https://github.com/param20h.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@param20h**](https://github.com/param20h) — Paramjit Singh | 🧭 **Project Lead** | Founded the project; core RAG architecture (FastAPI + ChromaDB + Next.js); Docker multi-stage & HuggingFace Spaces deployment; GitHub Actions CI/CD; JWT auth & Google OAuth; documentation with pipeline diagrams; project governance |
| <img src="https://github.com/Yuvraj-Sarathe.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@Yuvraj-Sarathe**](https://github.com/Yuvraj-Sarathe) — Yuvraj Sarathe | 📐 **Docs & Build** | Added Mermaid architecture diagram; inline RAG pipeline comments; `.env.example` docs; created `Makefile` with concurrent dev commands & `CHANGELOG.md` |
| <img src="https://github.com/SatyamPrakash09.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@SatyamPrakash09**](https://github.com/SatyamPrakash09) — Satyam Prakash | ⚙️ **Backend Engineer** | Chat history export & auto-refresh auth; user profile endpoints; `/health` endpoint (Vector DB + SQL DB monitoring); document pagination; MIME file validation; JWT access + refresh token system |
| <img src="https://github.com/akmhatey-ai.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@akmhatey-ai**](https://github.com/akmhatey-ai) | 🎨 **UI/UX** | Chat textarea auto-resize; clear messages on document switch |
| <img src="https://github.com/drishtisharma14052007-eng.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@drishtisharma14052007-eng**](https://github.com/drishtisharma14052007-eng) — Drishti Sharma | 📝 **Documentation** | GSSOC contributor FAQ content |
| <img src="https://github.com/Pika-pika06.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@Pika-pika06**](https://github.com/Pika-pika06) — Pika | 📝 **Documentation** | Changelog tracking historical commits through v0.4.0 |
| <img src="https://github.com/blinkerbit.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@blinkerbit**](https://github.com/blinkerbit) / [@algojogacor](https://github.com/algojogacor) — Arya Rizky | 🐛 **Bug Buster** | Fixed 0-indexed page number display in source cards |
| <img src="https://github.com/HirenGajjar.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@HirenGajjar**](https://github.com/HirenGajjar) | 🔒 **DevOps** | Restricted CORS origins via `ALLOWED_ORIGINS` environment variable |
| <img src="https://github.com/Kaustub26Pvgda.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@Kaustub26Pvgda**](https://github.com/Kaustub26Pvgda) — Kaustub Pavagada | ⚡ **Frontend Engineer** | Copy LLM response capability; increased max file upload size to 20 MB |
| <img src="https://github.com/akshy-yy.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@akshy-yy**](https://github.com/akshy-yy) — Akshaya | 🎨 **Frontend Engineer** | Typing indicator animation while AI responds |
| <img src="https://github.com/GHX5T-SOL.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@GHX5T-SOL**](https://github.com/GHX5T-SOL) — Bruce Wayne | 🐛 **Bug Buster** | Backend offline error message display |
| <img src="https://github.com/viswanatha.png?size=40" width="40" height="40" style="border-radius:50%"/> | [**@viswanatha**](https://github.com/viswanatha) | 📊 **Observability** | Health check endpoint |

</div>

<br/>

> 🌟 **Want to join them?** Check out [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and look for [good first issues](https://github.com/Yuvraj-Sarathe/PDF-Assistant-RAG/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) to get started!

---

<br/>

## 🌟 Overview

**PDF-Assistant-RAG** is a complete, production-ready AI document assistant that lets users upload complex PDFs, financial reports, legal contracts, and research papers — then chat with an AI that provides **accurate, cited answers** powered by a multi-stage Retrieval-Augmented Generation pipeline.

The system uses **semantic search + cross-encoder reranking** to find the most relevant document chunks, streams AI-generated answers token-by-token, and highlights exact source citations with page numbers — all inside a sleek Next.js UI with JWT-secured per-user data isolation.

<br/>

## 🏗️ Architecture

```mermaid
graph TD
    subgraph Frontend["Frontend (Next.js 16)"]
        UI["Dashboard UI (React)"]
        Chat["Chat Panel (SSE)"]
        Viewer["PDF Viewer (iframe)"]
    end

    subgraph Backend["Backend (FastAPI 0.115+)"]
        API["API Router (/api/v1)"]
        Auth["Auth (JWT/bcrypt)"]
        DB[(SQLite Metadata)]

        subgraph RAG["RAG Pipeline"]
            Upload["Ingestion Task (Chunking)"]
            Embed["Local Embeddings (all-MiniLM-L6-v2)"]
            Retriever["Two-Stage Retriever"]
            Rerank["Cross-Encoder Reranker"]
            Agent["Agent/Generator"]
        end
    end

    subgraph Storage["Vector Storage"]
        Chroma[(ChromaDB)]
    end

    subgraph External["External Services"]
        HF["HuggingFace Inference API (Qwen 72B)"]
    end

    %% Frontend to Backend Connections
    UI <-->|REST / Auth| API
    Chat <-->|SSE Streaming| API
    Viewer -->|Fetch PDF| API

    %% Backend Internals
    API <--> Auth
    API <--> DB
    API --> Upload
    API <--> Retriever
    API <--> Agent

    %% RAG Ingestion Flow
    Upload --> Embed
    Embed -->|Store Vectors| Chroma

    %% RAG Query Flow
    Retriever -->|1. Semantic Search| Chroma
    Retriever -->|2. Score & Sort| Rerank
    Retriever -->|Context| Agent

    %% External LLM Flow
    Agent <-->|LLM Generation| HF
```

<br/>

## 🛠 Tech Stack

<div align="center">

### Backend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=fastapi" width="30"/> | **FastAPI 0.115+** | Async REST API framework |
| <img src="https://skillicons.dev/icons?i=python" width="30"/> | **Python 3.11** | Runtime environment |
| <img src="https://skillicons.dev/icons?i=sqlite" width="30"/> | **SQLite + SQLAlchemy** | User & document metadata storage |
| <img src="https://img.shields.io/badge/JWT-000000?style=flat&logo=jsonwebtokens&logoColor=white" height="24"/> | **JWT + Passlib** | Authentication & authorization |
| <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=flat&logo=langchain&logoColor=white" height="24"/> | **LangChain** | RAG orchestration |
| <img src="https://img.shields.io/badge/ChromaDB-FF6B35?style=flat" height="24"/> | **ChromaDB** | Persistent vector store (per-user) |
| <img src="https://img.shields.io/badge/HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black" height="24"/> | **HuggingFace Hub** | LLM inference API |

### Frontend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=nextjs" width="30"/> | **Next.js 16** | React framework (App Router) |
| <img src="https://skillicons.dev/icons?i=tailwind" width="30"/> | **Tailwind CSS v4** | Utility-first styling |
| <img src="https://img.shields.io/badge/shadcn/ui-000000?style=flat&logo=shadcnui&logoColor=white" height="24"/> | **shadcn/ui** | Accessible component library |
| <img src="https://skillicons.dev/icons?i=ts" width="30"/> | **TypeScript** | Type-safe frontend |
| <img src="https://img.shields.io/badge/react--pdf-FF0000?style=flat" height="24"/> | **react-pdf** | In-browser PDF viewer |
| <img src="https://img.shields.io/badge/react--markdown-000000?style=flat" height="24"/> | **react-markdown + GFM** | Markdown-rendered AI responses |

### AI / ML Pipeline

| | Technology | Purpose |
|---|---|---|
| <img src="https://img.shields.io/badge/MiniLM-L6-v2-FFD21E?style=flat" height="24"/> | **all-MiniLM-L6-v2** | Local sentence embeddings |
| <img src="https://img.shields.io/badge/ms--marco--MiniLM-1C3C3C?style=flat" height="24"/> | **ms-marco-MiniLM-L-6-v2** | Cross-encoder reranker |
| <img src="https://img.shields.io/badge/Qwen2.5-72B-Instruct-626BDF?style=flat" height="24"/> | **Qwen2.5-72B-Instruct** | LLM (HuggingFace Inference API) |
| <img src="https://img.shields.io/badge/PyMuPDF-FF0000?style=flat" height="24"/> | **PyMuPDF + python-docx** | Document parsing |

### DevOps & Tooling

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=docker" width="30"/> | **Docker Multi-Stage** | Containerized deployment |
| <img src="https://skillicons.dev/icons?i=githubactions" width="30"/> | **GitHub Actions** | CI pipeline (dev branch) |
| <img src="https://skillicons.dev/icons?i=git" width="30"/> | **Git LFS** | Binary asset management |
| <img src="https://img.shields.io/badge/HuggingFace_Spaces-FFD21E?style=flat&logo=huggingface&logoColor=black" height="24"/> | **HuggingFace Spaces** | Production deployment |

</div>

<br/>

## ✨ Key Features

<table>
<tr>
<td width="33%" valign="top">

### 👤 Users
- 🔐 JWT-secured register & login
- 📄 Upload **PDF** and **DOCX** documents
- 💬 Ask questions in natural language
- 🌊 **Streaming AI responses** token-by-token
- 📚 Inline **source citations** with page numbers
- 🗂️ Per-user complete data isolation

</td>
<td width="33%" valign="top">

### 🤖 RAG Pipeline
- 🔪 Smart **recursive text chunking** (configurable size & overlap)
- 🧠 **Local embeddings** — no data leaves your machine
- 🔍 **Two-stage retrieval** — semantic search → cross-encoder rerank
- ✂️ Top-K filtering for precision answers
- 📝 Custom **system prompts** with citation instructions
- 🧾 Source scoring with confidence levels

</td>
<td width="33%" valign="top">

### ⚙️ Engineering
- 🚀 **Async FastAPI** with Server-Sent Events streaming
- 🗄️ **ChromaDB** with persistent per-user collections
- 🐳 **Multi-stage Docker** build (Node → Python)
- 🔄 **GitHub Actions CI** on `dev` branch
- 🛡️ CORS, file validation, JWT expiry
- 📊 Chat **history persistence** per document

</td>
</tr>
</table>

<br/>

## 📁 Project Structure

```
PDF-Assistant-RAG/
│
├── backend/                          # FastAPI + RAG server
│   ├── app/
│   │   ├── main.py                   # App entrypoint, middleware, static files
│   │   ├── config.py                 # Pydantic settings (env vars)
│   │   ├── database.py               # SQLAlchemy async engine
│   │   ├── models.py                 # ORM models (User, Document, Message)
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── auth.py                   # JWT creation & verification
│   │   │
│   │   ├── routes/
│   │   │   ├── auth.py               # POST /register, /login, /me
│   │   │   ├── documents.py          # Upload, list, delete, retrieve
│   │   │   └── chat.py               # Streaming chat + history
│   │   │
│   │   └── rag/
│   │       ├── agent.py              # Main RAG orchestrator
│   │       ├── chunker.py            # Recursive text splitter
│   │       ├── embeddings.py         # SentenceTransformer wrapper
│   │       ├── vectorstore.py        # ChromaDB collection manager
│   │       ├── retriever.py          # Semantic search + reranking
│   │       └── prompts.py            # System & user prompt templates
│   │
│   ├── requirements.txt
│   └── .env                          # Local env (never committed)
│
├── frontend/                         # Next.js 16 App Router
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout + fonts
│       │   ├── page.tsx              # Landing / redirect
│       │   ├── login/                # Auth pages
│       │   ├── register/
│       │   └── dashboard/            # Main app page
│       │
│       ├── components/
│       │   ├── chat/
│       │   │   ├── ChatPanel.tsx     # Chat UI + SSE streaming
│       │   │   ├── MessageBubble.tsx # User / assistant message
│       │   │   └── SourceCard.tsx    # Citation cards
│       │   ├── document/             # Upload + sidebar components
│       │   └── layout/               # Navbar, sidebar shell
│       │
│       └── lib/
│           └── api.ts                # Typed API client + SSE stream helper
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # CI — runs on dev branch only
│   │   ├── deploy.yml                # Docker build — main branch only
│   │   └── devsecops.yml             # Security scans — main branch only
│   ├── ISSUE_TEMPLATE/               # Bug report & feature request forms
│   ├── pull_request_template.md      # PR checklist
│   └── CODEOWNERS                    # Auto-review assignment
│
├── Dockerfile                        # Multi-stage: Node build → Python serve
├── docker-compose.yml                # Local Docker stack
├── CONTRIBUTING.md                   # contributor guide
└── .env.example                      # Template for environment variables
```

<br/>

## 🚀 Getting Started

### Prerequisites

- ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white) **Python 3.11+**
- ![Node.js](https://img.shields.io/badge/Node.js-20+-339933?style=flat&logo=node.js&logoColor=white) **Node.js 20+**
- ![HuggingFace](https://img.shields.io/badge/HuggingFace-Token-FFD21E?style=flat&logo=huggingface&logoColor=black) **HuggingFace account** (free) for LLM inference

---

### 1. Clone the Repository

```bash
git clone https://github.com/param20h/PDF-Assistant-RAG.git
cd PDF-Assistant-RAG
```

### 2. Configure Environment

```bash
cp .env.example backend/.env
```

Edit `backend/.env`:

```env
SECRET_KEY=your-strong-random-secret
DATABASE_URL=sqlite:///./data/app.db
HF_TOKEN=hf_your_huggingface_token_here
UPLOAD_DIR=./data/uploads
CHROMA_PERSIST_DIR=./data/chroma_db
```

> Get your free HuggingFace token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 3. Run Locally

Open **two terminals**:

```bash
# Terminal A — Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# → API running at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

```bash
# Terminal B — Frontend
cd frontend
npm install
npm run dev
# → App running at http://localhost:3000
```

### 4. Run with Docker

```bash
docker compose up --build
# → Full stack at http://localhost:7860
```

<br/>

## 🧠 RAG Pipeline

```
                    ┌─────────────────────────────────────────────┐
                    │              PDF / DOCX Upload               │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │         PyMuPDF / python-docx Parser         │
                    │         (text extraction per page)           │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │      Recursive Character Text Splitter       │
                    │   chunk_size=1000  |  overlap=200            │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │    all-MiniLM-L6-v2  (local embeddings)      │
                    │    384-dim dense vectors                      │
                    └───────────────────┬─────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │   ChromaDB  — per-user persistent collection │
                    └─────────────────────────────────────────────┘

                              ── At Query Time ──

  User Question ──▶ Embed ──▶ Semantic Search (Top-K=10)
                                        │
                                        ▼
                         Cross-Encoder Reranker (Top-K=5)
                         ms-marco-MiniLM-L-6-v2
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
| `POST` | `/api/v1/auth/login` | ❌ | Login and receive JWT token |
| `GET` | `/api/v1/auth/me` | ✅ | Get current user profile |
| `POST` | `/api/v1/documents/upload` | ✅ | Upload PDF/DOCX and trigger indexing |
| `GET` | `/api/v1/documents` | ✅ | List all documents for current user |
| `DELETE` | `/api/v1/documents/{id}` | ✅ | Delete a document and its vector data |
| `POST` | `/api/v1/chat/ask/stream` | ✅ | Ask a question (SSE streaming response) |
| `GET` | `/api/v1/chat/history/{doc_id}` | ✅ | Get chat history for a document |
| `DELETE` | `/api/v1/chat/history/{doc_id}` | ✅ | Clear chat history for a document |
| `GET` | `/health` | ❌ | Health check (db + chroma status) |

> Full interactive docs available at `/docs` (Swagger UI) when running locally.

<br/>

## 📦 Environment Variables

| Variable | Required | Default | Description | Where to Get It |
|---|---|---|---|---|
| `SECRET_KEY` | ✅ | — | JWT signing & session secret. Use a strong random string. | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `HF_TOKEN` | ✅ | — | HuggingFace API token for LLM inference via Inference API. | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (free) |
| `ENVIRONMENT` | ❌ | `development` | Runtime mode. Set to `production` for deployment to lock CORS. | — |
| `DEBUG` | ❌ | `False` | Enable debug mode with detailed error pages. Never enable in production. | — |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:3000,http://localhost:7860` | Comma-separated CORS origins (only enforced in production). | Your deployed domain(s) |
| `DATABASE_URL` | ❌ | `sqlite:///./data/app.db` | SQLAlchemy database connection string. | SQLite (default), or your Postgres/MySQL connection string |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT signing algorithm. | — |
| `JWT_EXPIRY_HOURS` | ❌ | `72` | JWT token lifetime in hours before re-login is required. | — |
| `UPLOAD_DIR` | ❌ | `./data/uploads` | Local directory for storing uploaded documents. | — |
| `MAX_FILE_SIZE_MB` | ❌ | `50` | Maximum allowed upload file size in MB. | — |
| `ALLOWED_EXTENSIONS` | ❌ | `pdf,docx,txt,md` | Comma-separated list of permitted file extensions. | — |
| `CHROMA_PERSIST_DIR` | ❌ | `./data/chroma_db` | Directory where ChromaDB persists its vector index. | — |
| `LLM_MODEL` | ❌ | `Qwen/Qwen2.5-72B-Instruct` | HuggingFace model ID for answer generation. | [huggingface.co/models](https://huggingface.co/models?inference=warm&sort=trending) |
| `LLM_TEMPERATURE` | ❌ | `0.3` | LLM sampling temperature (0 = deterministic, 1 = creative). | — |
| `LLM_MAX_NEW_TOKENS` | ❌ | `1024` | Maximum tokens per LLM response. | — |
| `EMBEDDING_MODEL` | ❌ | `sentence-transformers/all-MiniLM-L6-v2` | SentenceTransformer model for local embeddings (no external API). | [huggingface.co/sentence-transformers](https://huggingface.co/sentence-transformers) |
| `EMBEDDING_DIMENSION` | ❌ | `384` | Embedding vector dimension (must match the model). | — |
| `RERANKER_MODEL` | ❌ | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model for reranking retrieved chunks by relevance. | [huggingface.co/cross-encoder](https://huggingface.co/cross-encoder) |
| `CHUNK_SIZE` | ❌ | `1000` | Characters per document chunk. Larger = more context, smaller = better precision. | — |
| `CHUNK_OVERLAP` | ❌ | `200` | Overlap between consecutive chunks to maintain boundary context. | — |
| `TOP_K_RETRIEVAL` | ❌ | `10` | Candidate chunks retrieved from vector store during semantic search. | — |
| `TOP_K_RERANK` | ❌ | `5` | Final chunks passed to the LLM after reranking (must be ≤ `TOP_K_RETRIEVAL`). | — |

<br/>

## 📜 Scripts

### Backend (`backend/`)

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start FastAPI with hot reload |
| `uvicorn app.main:app --port 8000` | Start FastAPI on port 8000 |

### Frontend (`frontend/`)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start **Next.js** dev server |
| `npm run build` | Production build → `out/` (static export) |
| `npm run lint` | Run ESLint |

### Docker

| Command | Description |
|---------|-------------|
| `docker compose up --build` | Build and start the full stack |
| `docker compose down` | Stop all containers |

<br/>

## 🌐 Deployment

This project is deployed on **HuggingFace Spaces** using Docker.

### HuggingFace Spaces

1. Fork this repo and create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space) (SDK: Docker)
2. Set the following Space secrets:
   - `HF_TOKEN` — your HuggingFace API token
   - `SECRET_KEY` — a strong random string
3. Push to the `hf` remote — the Space will auto-build

```bash
git remote add hf https://<username>:<HF_TOKEN>@huggingface.co/spaces/<username>/<space-name>
git push hf main
```

### Self-Hosted / VPS

```bash
docker compose up -d --build
# App available at http://your-server:7860
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

**Built with 💙 as a flagship AI engineering project**

*If you found this project helpful, please give it a ⭐ — it helps contributors discover it!*

<br/>

[![FastAPI](https://skillicons.dev/icons?i=fastapi,python,nextjs,ts,tailwind,docker)](https://skillicons.dev)

<br/>

**[⬆ Back to top](#)**

</div>
