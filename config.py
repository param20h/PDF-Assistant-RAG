import os
from dotenv import load_dotenv

load_dotenv()

# ── App Config ───────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", b"T4tQj_3jK7z_gBqxZ1j_aGj8sFpXv_f4jZ8Rj9sPqG0=")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/rag_app")

# ── Upload Config ────────────────────────────────────
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

# ── RAG Config ───────────────────────────────────────
TOP_K = 5
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# ── Groq Config ──────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Google OAuth Config ──────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")