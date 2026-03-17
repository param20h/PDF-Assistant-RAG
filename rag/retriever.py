from google import genai
from google.genai import types
from pinecone import Pinecone
from config import TOP_K

# ── Gemini Embedding ─────────────────────────────────
def embed_query(query, gemini_key):
    """Generate query embedding using Gemini's gemini-embedding-001."""
    client = genai.Client(api_key=gemini_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query
    )
    return result.embeddings[0].values

# ── Retrieve Chunks from Pinecone ────────────────────
def retrieve_chunks(query, filename=None, user=None):
    """Query user's Pinecone index for relevant chunks."""
    if not user:
        return []

    gemini_key = user.get_gemini_key()
    pinecone_key = user.get_pinecone_key()
    index_name = user.pinecone_index_name

    if not gemini_key or not pinecone_key or not index_name:
        return []

    try:
        # Generate query embedding
        query_embedding = embed_query(query, gemini_key)

        # Connect to Pinecone
        pc = Pinecone(api_key=pinecone_key)
        index = pc.Index(index_name)

        # Build metadata filter
        filter_dict = None
        if filename:
            filter_dict = {"filename": {"$eq": filename}}

        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=TOP_K,
            namespace=user.username,
            filter=filter_dict,
            include_metadata=True
        )

        # Format results
        chunks = []
        if results.matches:
            max_score = max(m.score for m in results.matches) if results.matches else 1

            for match in results.matches:
                confidence = round((match.score / max_score) * 100, 2) if max_score > 0 else 0

                chunks.append({
                    "text": match.metadata.get("text", ""),
                    "filename": match.metadata.get("filename", ""),
                    "page": match.metadata.get("page", 1),
                    "score": round(match.score, 4),
                    "confidence": confidence
                })

        return chunks

    except Exception as e:
        print(f"Retrieval error: {e}")
        return []