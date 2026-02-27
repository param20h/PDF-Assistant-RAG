---
title: RAG PDF Assistant
emoji: 📄
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 📄 RAG PDF Assistant

A **Retrieval-Augmented Generation (RAG)** based document assistant built with Flask, FAISS, Sentence Transformers, Groq API, and Gemini. Upload PDFs, DOCX, or TXT files and intuitively chat with them using modern AI models.

---

## 🚀 Features

- 📂 **Multi-format Uploads**: Support for PDF, DOCX, and TXT files.
- 💬 **Interactive Chat**: Query and chat with your documents using AI.
- 🔍 **RAG-based Retrieval**: Fast and accurate chunk retrieval using FAISS.
- 🧠 **Multiple LLM Support**: Powered by Groq API (Llama 3 models) and Google Gemini.
- 🔐 **Robust Authentication**: Supports Google OAuth as well as standard Email/Password login.
- 🖼️ **User Profiles**: Custom profile picture uploads & Google profile pic sync.
- 👤 **Data Isolation**: Per-user file and vector store isolation for privacy.
- �️ **Admin Dashboard**: Admin panel to monitor users and uploaded files.
- �🗑️ **Data Management**: Intuitive UI to delete files and clear vector stores.
- 📱 **Responsive UI**: Minimal and modern front-end for seamless user experience.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Flask (Python) |
| **Authentication** | Flask-Login + Flask-Dance (Google OAuth) |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **Vector Store** | FAISS (CPU) |
| **LLMs** | Groq API & Google Gemini |
| **Frontend** | HTML, CSS, Vanilla JS |

---

## 📁 Project Structure

```text
RAG_App/
├── app.py                  # Main Flask application & routes
├── models.py               # Database models & user schema
├── config.py               # Configuration & env variables setup
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not committed)
├── rag/
│   ├── chunker.py          # Document parsing & chunking logic
│   ├── embeddings.py       # Vector embeddings generation & FAISS storage
│   ├── retriever.py        # Semantic search & chunk retrieval
│   └── generator.py        # LLM integration for answer generation
├── templates/
│   ├── index.html          # File management & upload dashboard
│   ├── chat.html           # RAG chat interface
│   ├── login.html          # User login page
│   ├── register.html       # User registration page
│   ├── admin.html          # Admin dashboard
│   └── profile.html        # User profile & settings dashboard
├── static/                 # Static assets (CSS, JS, profile_pics)
├── uploads/                # User-uploaded files (isolated per user)
└── vectorstore/            # FAISS vector database indices (isolated per user)
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/param20h/PDF-Assistant-RAG.git
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root of `RAG_App` (you can use `.env.example` as a template):
```env
SECRET_KEY=your_secure_secret_key
MONGO_URI=your_mongodb_uri_here  # If applicable, verify config.py
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```
*Note: Users can supply their own Groq and Gemini API keys directly via the app's Profile page!*

### 5. Run the Application
```bash
python app.py
```

### 6. Access in Browser
Visit `http://localhost:5000` in your web browser.

---

## 🔑 Obtaining API Credentials

| Service | Where to Get |
|---------|-------------|
| **Groq API Key** | [console.groq.com](https://console.groq.com) |
| **Gemini API Key**| [aistudio.google.com](https://aistudio.google.com) |
| **Google OAuth** | [console.cloud.google.com](https://console.cloud.google.com) |

### 🌐 Google OAuth Setup
1. Go to **Google Cloud Console**.
2. Create a new project and navigate to **APIs & Services** → **Credentials**.
3. Click **Create Credentials** → **OAuth Client ID**.
4. Set the Authorized redirect URI to: `http://localhost:5000/login/google/authorized`
5. Copy your `Client ID` and `Client Secret` into the `.env` file.

---

## 🔄 How It Works (The RAG Pipeline)

1. **Upload**: User uploads a document (PDF, DOCX, TXT).
2. **Chunking**: The document is parsed and split into manageable textual chunks.
3. **Embedding**: Chunks are converted to high-dimensional vectors using `all-MiniLM-L6-v2`.
4. **Vector Storage**: Vectors are indexed and stored using FAISS.
5. **Querying**: The user submits a question.
6. **Retrieval**: FAISS retrieves the most semantically relevant chunks to the question.
7. **Generation**: The retrieved context is passed to the selected LLM (Groq or Gemini) to generate an accurate, grounded answer.

---

## 🔐 DevSecOps Pipeline (Coming Soon)       

| Tool | Purpose |
|------|---------|
| `GitHub Actions` | CI/CD Pipeline tracking |
| `Bandit` | SAST - Python security vulnerability scanning |
| `Gitleaks` | Hardcoded secret and credential detection |
| `Trivy` | Container and dependency vulnerability checking |
| `Snyk` | Advanced dependency vulnerability scanning |
| `OWASP ZAP` | DAST - Dynamic web security scanning |
| `SonarCloud` | Overall code quality and security analysis |
| `Docker` | App containerization |

---

## 🐳 Docker (Coming Soon)

```bash
docker build -t rag-pdf-assistant .
docker run -p 5000:5000 rag-pdf-assistant
```

---

## 👨‍💻 Author

- **Name:** Paramjit Singh (param20h)

---

## 📄 License

This project is licensed under the **MIT License**. Check the `LICENSE` file for more details.

---

## ⭐ Show Some Support!

If you found this project helpful or inspiring, please give it a ⭐!