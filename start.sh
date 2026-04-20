#!/bin/bash
set -e

echo "🚀 Starting Document AI Analyst..."

# Navigate to backend directory
cd /app/backend

# Start FastAPI with uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 7860 \
    --workers 1 \
    --log-level info
