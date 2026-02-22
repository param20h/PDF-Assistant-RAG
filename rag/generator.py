import ollama
from config import MODEL_NAME

def build_prompt(question, chunks):
    context = ""

    for i, chunk in enumerate(chunks):
        context += f"\nchunk {i+1} (From: {chunk['filename']} Page: {chunk['page']}):\n"
        context += chunk["text"]
        context += "\n"


        prompt = f"""
        You are a helpful assistant. 
        Use the following context to answer the question.
        If you don't know the answer, say "I don't know".
        Do not make up answers.

        Context:
        {context}

        Question:
        {question}

        Answer:
        """

        return prompt
    

def call_llm(prompt):
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]

def generate_answer(question, chunks):
    if not chunks:
        return "no context found in the document."
    
    prompt = build_prompt(question, chunks)
    answer = call_llm(prompt)

    return answer
