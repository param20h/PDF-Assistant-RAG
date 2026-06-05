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

[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-VectorDB-000000?style=for-the-badge)](https://pinecone.io/)
[![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=for-the-badge)](https://console.groq.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-Embeddings-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com/)
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

The system uses **semantic search + cross-encoder reranking** to find the most relevant document chunks, streams AI-generated answers token-by-token, and highlights exact source citations with page numbers — all inside a clean Flask-served UI with session-based per-user data isolation.
<br/>

## 🏗️ Architecture

> Contributor note: see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a
> route-by-route system map, request-flow diagrams, ownership boundaries, and
> Swagger/OpenAPI documentation guidance.

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

### 🔄 System Flow Overview

1. The user interacts with the Next.js frontend to upload documents and ask questions.
2. FastAPI handles authentication, document ingestion, and chat APIs.
3. Uploaded documents are parsed, chunked, and converted into vector embeddings.
4. Embeddings are stored in ChromaDB for semantic retrieval.
5. During querying, the retriever fetches relevant chunks from ChromaDB.
6. A reranker improves retrieval quality before sending context to the LLM.
7. Hugging Face Inference API generates the final response.
8. Responses are streamed back to the frontend using SSE.

<br/>

## 🛠 Tech Stack

<div align="center">

### Backend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=flask" width="30"/> | **Flask 2.x** | Web framework + routing |
| <img src="https://skillicons.dev/icons?i=python" width="30"/> | **Python 3.11** | Runtime environment |
| <img src="https://skillicons.dev/icons?i=mongodb" width="30"/> | **MongoDB + PyMongo** | User accounts & metadata storage |
| <img src="https://img.shields.io/badge/Flask--Login-000000?style=flat" height="24"/> | **Flask-Login + Flask-Dance** | Session auth + Google OAuth |
| <img src="https://img.shields.io/badge/Pinecone-000000?style=flat" height="24"/> | **Pinecone** | Vector store (per-user namespace) |
| <img src="https://img.shields.io/badge/Google_Gemini-4285F4?style=flat&logo=google&logoColor=white" height="24"/> | **Google Gemini API** | Document chunk embeddings |
| <img src="https://img.shields.io/badge/Groq-F55036?style=flat" height="24"/> | **Groq (Llama 3)** | LLM answer generation |

### Frontend

| | Technology | Purpose |
|---|---|---|
| <img src="https://skillicons.dev/icons?i=html" width="30"/> | **Jinja2 (via Flask)** | Server-side HTML templating |
| <img src="https://skillicons.dev/icons?i=js" width="30"/> | **HTML + CSS + JavaScript** | Frontend UI (served from `/static` and `/templates`) |

### AI / ML Pipeline

| | Technology | Purpose |
|---|---|---|
| <img src="https://img.shields.io/badge/Google_Gemini-4285F4?style=flat&logo=google&logoColor=white" height="24"/> | **Google Gemini API** | Generates vector embeddings for document chunks |
| <img src="https://img.shields.io/badge/Pinecone-000000?style=flat" height="24"/> | **Pinecone** | Stores + retrieves embeddings per user namespace |
| <img src="https://img.shields.io/badge/Groq-F55036?style=flat" height="24"/> | **Groq API (Llama 3)** | Generates answers from retrieved context |
| <img src="https://img.shields.io/badge/PyMuPDF-FF0000?style=flat" height="24"/> | **PyMuPDF + pdfplumber + python-docx** | Document text extraction |

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
├── app.py                  # Flask app — all routes (upload, ask, download, auth)
├── config.py               # Loads SECRET_KEY, MONGO_URI, Google OAuth credentials
├── models.py               # User model (MongoDB via PyMongo)
├── make_admin.py           # CLI script to promote a user to admin
│
├── rag/
│   ├── chunker.py          # Splits PDF/DOCX/TXT into text chunks
│   ├── embeddings.py       # Gemini embeddings → Pinecone store/delete
│   ├── retriever.py        # Pinecone similarity search → top-K chunks
│   └── generator.py        # Groq LLM → answer from retrieved context
│
├── static/                 # CSS, JS, images
├── templates/              # Jinja2 HTML templates (login, register, chat, admin)
├── uploads/                # Per-user uploaded files (gitignored)
├── instance/               # Flask instance folder
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml          # CI — runs on dev branch only
│   │   ├── deploy.yml      # Docker build — main branch only
│   │   └── devsecops.yml   # Security scans — main branch only
│   ├── ISSUE_TEMPLATE/     # Bug report & feature request forms
│   └── pull_request_template.md
│
├── .env.example            # Template for required environment variables
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker build
├── docker-compose.yml      # Local Docker stack
├── start.sh                # Gunicorn startup script
└── render.yaml             # Render.com deployment config
```

<br/>

## 🚀 Getting Started

### Prerequisites

- ![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white) **Python 3.11+**
- ![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat&logo=mongodb&logoColor=white) **MongoDB** (Atlas free tier or local)
- ![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat) **Pinecone** account — [pinecone.io](https://pinecone.io)
- ![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat&logo=google&logoColor=white) **Google Gemini API key** — [aistudio.google.com](https://aistudio.google.com)
- ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat) **Groq API key** — [console.groq.com](https://console.groq.com)

---

### 1. Clone the Repository

```bash
git clone https://github.com/param20h/PDF-Assistant-RAG.git
cd PDF-Assistant-RAG
```

### 2. Configure Environment

```bash
cp .env.example .env

Edit `.env`:

SECRET_KEY=your-strong-random-secret
DATABASE_URL=sqlite:///./data/app.db
HF_TOKEN=hf_your_huggingface_token_here
UPLOAD_DIR=./data/uploads
CHROMA_PERSIST_DIR=./data/chroma_db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

> Get your free HuggingFace token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

#### Email Verification Setup

Password registration requires email verification before users can log in. To send real verification emails, add SMTP settings to `backend/.env`:

```env
FRONTEND_URL=http://localhost:3000
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_or_gmail_app_password
MAIL_FROM=your_sender_email@example.com
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

For Gmail, enable 2-Step Verification on the sender Google account, create a 16-character App Password from Google Account > Security > App passwords, then use:

```env
MAIL_USERNAME=yourgmail@gmail.com
MAIL_PASSWORD=your_16_character_app_password
MAIL_FROM=yourgmail@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

Without SMTP settings in a non-production environment, registration returns a local verification link so contributors can test the flow without private email credentials. With SMTP configured, the same link is sent by email.

### 3. Set up crawl4ai (URL Upload Feature)

The URL upload feature (`POST /api/v1/documents/urlupload`) uses **crawl4ai** with a Playwright browser to crawl web pages. `crawl4ai-setup` handles the Playwright browser installation automatically — run it once after `pip install`:

```bash
crawl4ai-setup
```


---

### 3. Run Locally

```bash
# Single terminal — Flask app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# → App running at http://localhost:5000
```

### 4. Run with Docker

```bash
docker compose up --build
# → App running at http://localhost:7860
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
| `POST` | `/api/v1/documents/upload` | ✅ | Upload PDF/DOCX and enqueue background indexing (`202 Accepted`) |
| `GET` | `/api/v1/documents` | ✅ | List all documents for current user |
| `GET` | `/api/v1/documents/{id}/status` | ✅ | Poll background document processing status |
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
| `HF_CLIENT_ID` | ❌ | — | HuggingFace OAuth client ID. Required only for Hugging Face sign-in. | [HuggingFace Developer Settings](https://huggingface.co/settings/connected-applications) |
| `HF_CLIENT_SECRET` | ❌ | — | HuggingFace OAuth client secret. Required only for Hugging Face sign-in. | [HuggingFace Developer Settings](https://huggingface.co/settings/connected-applications) |
| `HF_REDIRECT_URI` | ❌ | `http://localhost:8000/api/v1/auth/callback/huggingface` | HuggingFace OAuth callback redirect URI. | — |
| `FRONTEND_URL` | ❌ | `http://localhost:3000` | Public frontend URL used for OAuth redirects and email verification links. | Your deployed frontend URL |
| `ENVIRONMENT` | ❌ | `development` | Runtime mode. Set to `production` for deployment to lock CORS. | — |
| `DEBUG` | ❌ | `False` | Enable debug mode with detailed error pages. Never enable in production. | — |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:3000,http://localhost:7860` | Comma-separated CORS origins (only enforced in production). | Your deployed domain(s) |
| `DATABASE_URL` | ❌ | `sqlite:///./data/app.db` | SQLAlchemy database connection string. | SQLite (default), or your Postgres/MySQL connection string |
| `JWT_ALGORITHM` | ❌ | `HS256` | JWT signing algorithm. | — |
| `JWT_EXPIRY_HOURS` | ❌ | `72` | JWT token lifetime in hours before re-login is required. | — |
| `GOOGLE_CLIENT_ID` | ❌ | — | Google OAuth web client ID used by FastAPI to verify ID tokens. | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | ❌ | — | Google OAuth web client ID exposed to the Next.js Google sign-in button. | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | ❌ | `24` | Email verification token lifetime in hours. | — |
| `MAIL_USERNAME` | ❌ | — | SMTP username for account verification emails. | SMTP provider or Gmail App Password setup |
| `MAIL_PASSWORD` | ❌ | — | SMTP password or Gmail 16-character App Password. | SMTP provider or Gmail App Password setup |
| `MAIL_FROM` | ❌ | — | Sender email address for verification emails. | Verified sender address |
| `MAIL_SERVER` | ❌ | — | SMTP server hostname, for example `smtp.gmail.com`. | SMTP provider |
| `MAIL_PORT` | ❌ | `587` | SMTP server port. | SMTP provider |
| `MAIL_STARTTLS` | ❌ | `True` | Enable STARTTLS for SMTP. | SMTP provider |
| `MAIL_SSL_TLS` | ❌ | `False` | Enable SSL/TLS for SMTP. | SMTP provider |
| `CELERY_BROKER_URL` | ❌ | `redis://localhost:6379/0` | Redis broker URL used by FastAPI to queue document ingestion jobs. | Redis |
| `CELERY_RESULT_BACKEND` | ❌ | `redis://localhost:6379/1` | Redis backend URL used by Celery to store task state/results. | Redis |
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
| `python scripts/run_ragas_eval.py --user-id <user-id>` | Run the 50-question RAGAS comparison for vector search vs GraphRAG |

The RAGAS script reads `backend/evaluation/ragas_sample_questions.jsonl`,
generates answers from standard vector contexts and vector-plus-GraphRAG
contexts, then writes aggregate scores to `backend/evaluation/ragas_results.json`.
Pass `--document-id <document-id>` to evaluate one indexed document.

### Frontend (`frontend/`)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start **Next.js** dev server |
| `npm run build` | Production build → `out/` (static export) |
| `npm run lint` | Run ESLint |
| `npm run test:e2e` | Run Playwright end-to-end tests |

### Docker

| Command | Description |
|---------|-------------|
| `docker compose --profile cpu up --build` | Build and start the full stack (CPU-only, no GPU required) |
| `docker compose --profile gpu up --build` | Build and start the full stack with NVIDIA GPU acceleration |
| `docker compose --profile debug up` | Also start pgAdmin at http://localhost:5050 |
| `docker compose down` | Stop all containers |

> **CPU profile** — works on any machine. Embeddings run on CPU via `all-MiniLM-L6-v2`.  
> **GPU profile** — requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html). Sets `DEVICE=cuda` for accelerated embedding inference.

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

[![Stack](https://skillicons.dev/icons?i=flask,python,mongodb,docker)](https://skillicons.dev)

<br/>

**[⬆ Back to top](#)**

</div>
