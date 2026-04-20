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

# 🧠 Document AI Analyst — Enterprise Agentic RAG System

Upload complex PDFs, financial reports, legal contracts, or research papers and chat with an AI agent that provides **accurate, cited insights** powered by Retrieval-Augmented Generation.

## ✨ Features

- **Multi-Format Upload** — PDF, DOCX, TXT, Markdown with smart chunking
- **Semantic Search** — Two-stage retrieval with cross-encoder reranking
- **Streaming Chat** — Real-time AI responses with inline source citations
- **Data Isolation** — Per-user vector collections for complete privacy
- **Open-Source LLMs** — Powered by Mistral-7B and HuggingFace ecosystem

## 🏗️ Architecture

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, Tailwind CSS v4, Shadcn UI v2 |
| **Backend** | FastAPI, SQLAlchemy, JWT Auth |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 (local) |
| **Vector Store** | ChromaDB (persistent, per-user collections) |
| **Reranker** | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| **LLM** | Mistral-7B-Instruct via HuggingFace Inference API |
| **Deployment** | Docker multi-stage build on HuggingFace Spaces |

## 🚀 Quick Start

1. **Register** an account
2. **Upload** a PDF document
3. **Wait** for processing (chunking + embedding)
4. **Ask** questions and get cited answers!

## 🔧 Local Development

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 7860

# Frontend
cd frontend && npm install && npm run dev
```

## 📦 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `HF_TOKEN` | ✅ | HuggingFace API token for LLM inference |
| `SECRET_KEY` | ✅ | JWT signing secret |
| `DATABASE_URL` | ❌ | SQLite path (default: `sqlite:///./data/app.db`) |

## 🛠️ Tech Stack

Built with: **FastAPI** • **LangChain** • **ChromaDB** • **HuggingFace** • **Next.js 16** • **Tailwind CSS** • **Shadcn UI**