import os 
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:latest")

EMBEDDING_MODEL = "all-MiniLM-L6-V2"

SECRET_KEY = "your_secret_key_here"
SQLALCHEMY_DATABASE_URI = "sqlite:///users.db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

UPLOAD_FOLDER = "uploads"
CHROMA_DB_PATH = "vectorstore"

TOP_K = 10