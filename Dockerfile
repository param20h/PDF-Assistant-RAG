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
COPY backend/ ./backend/

# Copy frontend build from stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Create data directories
RUN mkdir -p data/uploads data/chroma_db

# Copy entrypoint
COPY start.sh ./start.sh
RUN chmod +x start.sh

# HuggingFace Spaces requires port 7860
EXPOSE 7860

# Entrypoint
CMD ["./start.sh"]
