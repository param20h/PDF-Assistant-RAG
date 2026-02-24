import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # ← Load .env file first

from groq import Groq
from config import GROQ_MODEL

def get_groq_client(user_key):
    if not user_key:
        raise ValueError("No Groq API Key available. Please add it to your profile.")
    return Groq(api_key=user_key)

def generate_answer(question, context_chunks, user=None):
    try:
        if not context_chunks:
            context = "No specific document context found for this query."
        else:
            context = "\n\n".join([
                f"📄 File: {chunk['filename']} | Page: {chunk['page']}\n{chunk['text']}"
                for chunk in context_chunks
            ])

        prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided document context.

Document Context:
{context}

User Question: {question}

Instructions:
- If the question is a greeting or general chat (like "hi" or "how are you"), just reply naturally and explain you are here to help with their PDF documents.
- If the question is about the document, use the provided context to answer.
- If the context doesn't contain the answer, just say you couldn't find it in the document.
- Try to be clear, helpful, and concise.

Answer:"""

        pref_model = user.preferred_model if user else "groq"
        
        if pref_model == "gemini":
            key = user.get_gemini_key() if user else None
            if not key:
                return "❌ No Gemini API key available. Please add it in your Profile settings."
            
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash") # Fast & Free Gemini Model
            response = model.generate_content(prompt)
            return response.text
        else:
            key = user.get_groq_key() if user else None
            client = get_groq_client(key)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful document assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error generating answer: {str(e)}"