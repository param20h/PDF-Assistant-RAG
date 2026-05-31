# syntax=docker/dockerfile:1

# --------------------------------------------------------
# Stage 1: Build Next.js frontend assets
# --------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# --------------------------------------------------------
# Stage 2: Build Python dependencies in an isolated venv
# --------------------------------------------------------
FROM python:3.11-slim AS python-builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# --------------------------------------------------------
# Stage 3: Runtime image with only app code and artifacts
# --------------------------------------------------------
FROM python:3.11-slim

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/data/huggingface
ENV TRANSFORMERS_CACHE=/app/data/huggingface

# HuggingFace Spaces runs as user 1000
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Runtime-only system packages. Build tools stay in python-builder.
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /opt/venv /opt/venv

# Copy backend code
COPY backend/app ./backend/app
COPY backend/__init__.py ./backend/__init__.py

# Copy frontend build from stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Create data directories with proper permissions
RUN mkdir -p /app/data/uploads /app/data/chroma_db /app/data/graphs /app/data/huggingface && \
    chown -R appuser:appuser /app

# Copy entrypoint
COPY start.sh ./start.sh
RUN chmod +x start.sh

# Switch to non-root user
USER appuser

# HuggingFace Spaces requires port 7860
EXPOSE 7860

CMD ["./start.sh"]
