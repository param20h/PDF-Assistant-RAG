# 📄 RAG PDF Assistant

A **Retrieval-Augmented Generation (RAG)** document assistant built with Flask, Pinecone, Gemini Embeddings, Groq API, and Google Gemini. Upload PDFs, DOCX, TXT, or MD files and intuitively chat with them using modern AI models.

---

## 🚀 Features

- 📂 **Multi-format Uploads**: Support for PDF, DOCX, TXT, and Markdown files.
- 💬 **Interactive Chat**: Query and chat with your documents using AI.
- 🔍 **RAG-based Retrieval**: Fast and accurate semantic search using Pinecone vector database.
- 🧠 **Multiple LLM Support**: Powered by Groq API (Llama 3) and Google Gemini.
- 🔐 **Robust Authentication**: Supports Google OAuth as well as standard Email/Password login.
- 🖼️ **User Profiles**: Custom profile picture uploads & Google profile pic sync.
- 👤 **Data Isolation**: Per-user namespaces in Pinecone for complete privacy.
- 🛡️ **Admin Dashboard**: Admin panel to monitor users and uploaded files.
- 🗑️ **Data Management**: Intuitive UI to delete files and clear vector stores.
- 📱 **Responsive UI**: Minimal and modern front-end for seamless user experience.
- ☁️ **Lightweight & Cloud-Native**: Zero local ML models — all embeddings and LLM calls are cloud-based API calls, requiring minimal server RAM.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Flask (Python) |
| **Authentication** | Flask-Login + Flask-Dance (Google OAuth) |
| **Embeddings** | Google Gemini (`gemini-embedding-001`) |
| **Vector Store** | Pinecone (Serverless) |
| **LLMs** | Groq API (Llama 3.3 70B) & Google Gemini |
| **User Database** | MongoDB Atlas |
| **Frontend** | HTML, CSS, Vanilla JS |

---

## 📁 Project Structure

```text
RAG_App/
├── app.py                  # Main Flask application & routes
├── models.py               # MongoDB user model & encrypted key storage
├── config.py               # Configuration & env variables
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment blueprint
├── Dockerfile              # Docker containerization
├── .env.example            # Environment variable template
├── rag/
│   ├── chunker.py          # Document parsing & chunking logic
│   ├── embeddings.py       # Gemini embeddings + Pinecone upsert
│   ├── retriever.py        # Pinecone semantic search & retrieval
│   └── generator.py        # LLM integration for answer generation
├── templates/
│   ├── index.html          # File management & upload dashboard
│   ├── chat.html           # RAG chat interface
│   ├── login.html          # User login page
│   ├── register.html       # User registration page
│   ├── admin.html          # Admin dashboard
│   └── profile.html        # User profile & API key settings
├── static/                 # Static assets (CSS, JS, profile_pics)
├── uploads/                # User-uploaded files (isolated per user)
└── .github/workflows/
    ├── devsecops.yml       # Security scanning pipeline
    └── deploy.yml          # Docker build & GHCR push pipeline
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/param20h/PDF-Assistant-RAG.git
cd PDF-Assistant-RAG
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
Create a `.env` file using the template:
```bash
cp .env.example .env
```

Fill in the required server-side variables:
```env
SECRET_KEY=your_secure_random_key
ENCRYPTION_KEY=your_fernet_key
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/rag_app
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

> **Generate keys:**
> ```bash
> # SECRET_KEY
> python -c "import secrets; print(secrets.token_hex(32))"
> # ENCRYPTION_KEY
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

### 5. Run the Application
```bash
python app.py
```

### 6. Access in Browser
Visit `http://localhost:5000` in your web browser.

---

## 🔑 User Setup (Per-User API Keys)

After registering/logging in, each user must add their own API keys on the **Profile** page:

| Service | Required? | Where to Get | Notes |
|---------|-----------|--------------|-------|
| **Gemini API Key** | ✅ Required | [aistudio.google.com](https://aistudio.google.com) | Free — used for embeddings & chat |
| **Pinecone API Key** | ✅ Required | [app.pinecone.io](https://app.pinecone.io) | Free tier available |
| **Pinecone Index Name** | ✅ Required | Pinecone Dashboard | Create: dim `3072`, metric `cosine` |
| **Groq API Key** | Optional | [console.groq.com](https://console.groq.com) | For Llama 3 chat generation |

### 🌲 Pinecone Index Setup
1. Create a free account at [pinecone.io](https://app.pinecone.io)
2. Create a **Serverless** index with:
   - **Dimension**: `3072`
   - **Metric**: `cosine`
3. Copy your API key and index name into the Profile page

---

## 🌐 Google OAuth Setup
1. Go to **Google Cloud Console** → [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project and navigate to **APIs & Services** → **Credentials**
3. Click **Create Credentials** → **OAuth Client ID**
4. Set the Authorized redirect URI to: `http://localhost:5000/login/google/authorized`
5. Copy your `Client ID` and `Client Secret` into the `.env` file

---

## 🔄 How It Works (The RAG Pipeline)

1. **Upload**: User uploads a document (PDF, DOCX, TXT, or MD).
2. **Chunking**: The document is parsed and split into manageable textual chunks.
3. **Embedding**: Chunks are converted to 3072-dimensional vectors using `gemini-embedding-001`.
4. **Vector Storage**: Vectors are stored in the user's Pinecone namespace.
5. **Querying**: The user submits a question.
6. **Retrieval**: Pinecone retrieves the most semantically relevant chunks.
7. **Generation**: The retrieved context is passed to the selected LLM (Groq or Gemini) to generate an accurate, grounded answer.

---

## 🚀 Deployment

### Deploy to Render (Recommended — Free)
1. Push your code to GitHub
2. Go to [Render](https://dashboard.render.com) → **New** → **Web Service**
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` and configures everything
5. Add environment variables: `SECRET_KEY`, `ENCRYPTION_KEY`, `MONGO_URI`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
6. Update Google OAuth redirect URI to: `https://your-app.onrender.com/login/google/authorized`
7. Deploy!

### Deploy with Docker
```bash
docker build -t rag-app .
docker run -p 5000:5000 --env-file .env rag-app
```

---

## 🔐 DevSecOps Pipeline

| Tool | Purpose |
|------|---------|
| `GitHub Actions` | CI/CD Pipeline |
| `Bandit` | SAST — Python security vulnerability scanning |
| `Gitleaks` | Hardcoded secret and credential detection |
| `Trivy` | Container and dependency vulnerability checking |
| `Snyk` | Advanced dependency vulnerability scanning |
| `OWASP ZAP` | DAST — Dynamic web security scanning |
| `SonarCloud` | Overall code quality and security analysis |
| `GHCR` | Docker image hosting via GitHub Container Registry |

---

## 👨‍💻 Author

- **Name:** Paramjit Singh (param20h)

---

## 📄 License

This project is licensed under the **MIT License**. Check the `LICENSE` file for more details.

---

## ⭐ Show Some Support!

If you found this project helpful or inspiring, please give it a ⭐!