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

<br/>

<div align="center">
  <a href="https://github.com/param20h/PDF-Assistant-RAG/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=param20h/PDF-Assistant-RAG" alt="Contributors" />
  </a>
</div>

<br/>

> 🌟 **GSSOC Contributors** — This project is open for [GirlScript Summer of Code](https://gssoc.girlscript.tech/). Check out our [CONTRIBUTING.md](CONTRIBUTING.md) to get started and browse [open issues](https://github.com/param20h/PDF-Assistant-RAG/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) tagged `good first issue`.

---

<br/>

## 🌟 Overview

**PDF-Assistant-RAG** is a complete, production-ready AI document assistant that lets users upload complex PDFs, financial reports, legal contracts, and research papers — then chat with an AI that provides **accurate, cited answers** powered by a multi-stage Retrieval-Augmented Generation pipeline.

The system uses **semantic search + cross-encoder reranking** to find the most relevant document chunks, streams AI-generated answers token-by-token, and highlights exact source citations with page numbers — all inside a sleek Next.js UI with JWT-secured per-user data isolation.

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
├── CONTRIBUTING.md                   # GSSOC contributor guide
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

| Variable | Required | Default | Description |
|---|---|---|---|
| `HF_TOKEN` | ✅ | — | HuggingFace API token for LLM inference |
| `SECRET_KEY` | ✅ | — | JWT signing secret (use a strong random string) |
| `DATABASE_URL` | ❌ | `sqlite:///./data/app.db` | SQLAlchemy database URL |
| `UPLOAD_DIR` | ❌ | `./data/uploads` | Directory for uploaded files |
| `CHROMA_PERSIST_DIR` | ❌ | `./data/chroma_db` | ChromaDB persistence path |
| `LLM_MODEL` | ❌ | `Qwen/Qwen2.5-72B-Instruct` | HuggingFace model ID |
| `LLM_TEMPERATURE` | ❌ | `0.3` | LLM sampling temperature |
| `LLM_MAX_NEW_TOKENS` | ❌ | `1024` | Max tokens per response |
| `EMBEDDING_MODEL` | ❌ | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `CHUNK_SIZE` | ❌ | `1000` | Document chunk size (characters) |
| `CHUNK_OVERLAP` | ❌ | `200` | Overlap between chunks |
| `TOP_K_RETRIEVAL` | ❌ | `10` | Candidates retrieved from vector store |
| `TOP_K_RERANK` | ❌ | `5` | Final chunks passed to LLM after reranking |
| `MAX_FILE_SIZE_MB` | ❌ | `50` | Maximum upload file size |

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

## 🤝 Contributing — GSSOC

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

*If you found this project helpful, please give it a ⭐ — it helps GSSOC contributors discover it!*

<br/>

[![FastAPI](https://skillicons.dev/icons?i=fastapi,python,nextjs,ts,tailwind,docker)](https://skillicons.dev)

<br/>

**[⬆ Back to top](#)**

</div>