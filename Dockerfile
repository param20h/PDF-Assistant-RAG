# ════════════════════════════════════════════════════════
# Stage 1: Build Next.js Frontend
# ════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# ════════════════════════════════════════════════════════
# Stage 2: Python Backend + Serve Frontend
# ════════════════════════════════════════════════════════
FROM python:3.11-slim

# HuggingFace Spaces runs as user 1000
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app ./backend/app
COPY backend/__init__.py ./backend/__init__.py

# Copy frontend build from stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Create data directories with proper permissions
RUN mkdir -p /app/data/uploads /app/data/chroma_db && \
    chown -R appuser:appuser /app

# Copy entrypoint
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Switch to non-root user
USER appuser

# Pre-download models during build for faster startup
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" 2>/dev/null || true

# HuggingFace Spaces requires port 7860
EXPOSE 7860

ENV PYTHONUNBUFFERED=1

CMD ["./start.sh"]
