#!/usr/bin/env python3
"""
Pre-download the Hugging Face model to the local cache.
Run this in CI before starting the application so the app does not block
during startup downloading model artifacts.
"""
from huggingface_hub import snapshot_download
from app.config import get_settings

def main():
    settings = get_settings()
    model = settings.EMBEDDING_MODEL
    print(f"Prefetching Hugging Face model: {model}")
    # snapshot_download will fetch model files into HF cache (~~/.cache/huggingface)
    # set resume_download=True to continue partial downloads if present.
    snapshot_download(repo_id=model, resume_download=True)
    print("Prefetch complete")

if __name__ == "__main__":
    main()