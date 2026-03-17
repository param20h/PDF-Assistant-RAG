from google import genai
from google.genai import types
from pinecone import Pinecone
from config import CHUNK_SIZE, CHUNK_OVERLAP

# ── Gemini Embedding ─────────────────────────────────
def embed_text(text, gemini_key):
    """Generate embedding using Gemini's free gemini-embedding-001 model."""
    client = genai.Client(api_key=gemini_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values  # 3072-dimensional vector

# ── Get Pinecone Index ───────────────────────────────
def get_pinecone_index(pinecone_key, index_name):
    """Connect to user's Pinecone index."""
    pc = Pinecone(api_key=pinecone_key)
    return pc.Index(index_name)

# ── Store Embeddings in Pinecone ─────────────────────
def store_embeddings(chunks, filename, user):
    """Embed chunks using Gemini and upsert into user's Pinecone index."""
    gemini_key = user.get_gemini_key()
    pinecone_key = user.get_pinecone_key()
    index_name = user.pinecone_index_name

    if not gemini_key:
        raise ValueError("Gemini API key is required for embeddings. Please add it in your Profile.")
    if not pinecone_key or not index_name:
        raise ValueError("Pinecone API key and index name are required. Please add them in your Profile.")

    index = get_pinecone_index(pinecone_key, index_name)
    namespace = user.username

    # Batch upsert vectors
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vectors = []

        for j, chunk in enumerate(batch):
            embedding = embed_text(chunk["text"], gemini_key)
            vector_id = f"{filename}_{i + j}"

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "filename": filename,
                    "page": chunk["page"],
                    "chunk_index": i + j
                }
            })

        index.upsert(vectors=vectors, namespace=namespace)

# ── Delete Vectors by Filename ───────────────────────
def delete_embeddings(filename, user):
    """Delete all vectors for a specific file from user's Pinecone index."""
    pinecone_key = user.get_pinecone_key()
    index_name = user.pinecone_index_name

    if not pinecone_key or not index_name:
        return

    index = get_pinecone_index(pinecone_key, index_name)
    namespace = user.username

    try:
        dummy_vector = [0.0] * 3072
        results = index.query(
            vector=dummy_vector,
            top_k=10000,
            namespace=namespace,
            filter={"filename": {"$eq": filename}},
            include_metadata=False
        )
        
        if results.matches:
            ids_to_delete = [match.id for match in results.matches]
            index.delete(ids=ids_to_delete, namespace=namespace)
    except Exception as e:
        print(f"Error deleting embeddings: {e}")

# ── Clear All Vectors for User ───────────────────────
def clear_all_embeddings(user):
    """Delete all vectors in user's namespace."""
    pinecone_key = user.get_pinecone_key()
    index_name = user.pinecone_index_name

    if not pinecone_key or not index_name:
        return

    index = get_pinecone_index(pinecone_key, index_name)
    index.delete(delete_all=True, namespace=user.username)