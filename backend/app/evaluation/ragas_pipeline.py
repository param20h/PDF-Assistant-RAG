"""RAGAS evaluation pipeline for vector search versus GraphRAG."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable, Optional

from huggingface_hub import InferenceClient

from app.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.graph_retriever import get_entity_context
from app.rag.vectorstore import query_chunks

settings = get_settings()


AnswerGenerator = Callable[[str, list[str]], str]


@dataclass(frozen=True)
class EvaluationQuestion:
    id: str
    question: str
    reference: str


@dataclass(frozen=True)
class EvaluationRecord:
    id: str
    mode: str
    question: str
    reference: str
    response: str
    contexts: list[str]


def load_questions(dataset_path: Path, limit: int = 50) -> list[EvaluationQuestion]:
    """Load a JSONL RAGAS dataset and validate the required fields."""
    questions: list[EvaluationQuestion] = []

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            missing = {"id", "question", "reference"} - set(row)
            if missing:
                fields = ", ".join(sorted(missing))
                raise ValueError(f"Line {line_number} is missing required field(s): {fields}")

            questions.append(
                EvaluationQuestion(
                    id=str(row["id"]),
                    question=str(row["question"]).strip(),
                    reference=str(row["reference"]).strip(),
                )
            )

            if len(questions) >= limit:
                break

    if len(questions) < limit:
        raise ValueError(f"Expected {limit} evaluation questions, found {len(questions)}")

    return questions


def retrieve_vector_contexts(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
) -> list[str]:
    """Retrieve plain vector-search contexts for a question."""
    query_embedding = embed_query(question)
    chunks = query_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        document_id=document_id,
        top_k=top_k or settings.TOP_K_RETRIEVAL,
    )
    return _chunk_texts(chunks)


def retrieve_graphrag_contexts(
    question: str,
    user_id: str,
    document_id: Optional[str] = None,
    top_k: Optional[int] = None,
) -> list[str]:
    """Retrieve vector contexts and append GraphRAG relationship context."""
    contexts = retrieve_vector_contexts(
        question=question,
        user_id=user_id,
        document_id=document_id,
        top_k=top_k,
    )
    graph_context = get_entity_context(
        query=question,
        user_id=user_id,
        document_id=document_id,
    )
    return append_graph_context(contexts, graph_context)


def append_graph_context(contexts: list[str], graph_context: str) -> list[str]:
    """Return contexts plus graph context when GraphRAG found relationships."""
    clean_graph_context = graph_context.strip()
    if not clean_graph_context:
        return contexts
    return [*contexts, clean_graph_context]


def generate_grounded_answer(question: str, contexts: list[str]) -> str:
    """Generate an answer using only retrieved contexts."""
    if not contexts:
        return "I do not have enough retrieved context to answer this question."

    client = InferenceClient(token=settings.HF_TOKEN)
    context_block = "\n\n".join(
        f"Context {index}:\n{context}" for index, context in enumerate(contexts, start=1)
    )
    prompt = (
        "Answer the question using only the provided context. "
        "If the context is insufficient, say that the answer is not available in the context.\n\n"
        f"{context_block}\n\nQuestion: {question}"
    )
    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are a careful RAG evaluator that only uses supplied evidence.",
            },
            {"role": "user", "content": prompt},
        ],
        model=settings.LLM_MODEL,
        max_tokens=min(settings.LLM_MAX_NEW_TOKENS, 512),
        temperature=0.0,
    )
    if not response.choices:
        return ""
    return (response.choices[0].message.content or "").strip()


def collect_records(
    questions: Iterable[EvaluationQuestion],
    user_id: str,
    document_id: Optional[str] = None,
    answer_generator: AnswerGenerator = generate_grounded_answer,
) -> dict[str, list[EvaluationRecord]]:
    """Build vector and GraphRAG samples ready for RAGAS."""
    grouped: dict[str, list[EvaluationRecord]] = {"vector": [], "graphrag": []}

    for item in questions:
        vector_contexts = retrieve_vector_contexts(
            question=item.question,
            user_id=user_id,
            document_id=document_id,
        )
        graphrag_contexts = retrieve_graphrag_contexts(
            question=item.question,
            user_id=user_id,
            document_id=document_id,
        )

        grouped["vector"].append(
            EvaluationRecord(
                id=item.id,
                mode="vector",
                question=item.question,
                reference=item.reference,
                response=answer_generator(item.question, vector_contexts),
                contexts=vector_contexts,
            )
        )
        grouped["graphrag"].append(
            EvaluationRecord(
                id=item.id,
                mode="graphrag",
                question=item.question,
                reference=item.reference,
                response=answer_generator(item.question, graphrag_contexts),
                contexts=graphrag_contexts,
            )
        )

    return grouped


def evaluate_records(records: list[EvaluationRecord]) -> dict[str, float]:
    """Run RAGAS over collected records and return mean metric scores."""
    from langchain_huggingface import HuggingFaceEndpoint
    from ragas import EvaluationDataset, evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, FactualCorrectness, LLMContextRecall

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": record.question,
                "retrieved_contexts": record.contexts,
                "response": record.response,
                "reference": record.reference,
            }
            for record in records
        ]
    )
    evaluator_llm = LangchainLLMWrapper(
        HuggingFaceEndpoint(
            repo_id=settings.LLM_MODEL,
            huggingfacehub_api_token=settings.HF_TOKEN,
            max_new_tokens=512,
            temperature=0.0,
            timeout=300,
        )
    )
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            FactualCorrectness(),
            LLMContextRecall(),
        ],
        llm=evaluator_llm,
    )
    return summarize_ragas_result(result)


def compare_pipelines(grouped_records: dict[str, list[EvaluationRecord]]) -> dict[str, Any]:
    """Evaluate both retrieval modes and include metric deltas."""
    vector_scores = evaluate_records(grouped_records["vector"])
    graphrag_scores = evaluate_records(grouped_records["graphrag"])
    metrics = sorted(set(vector_scores) | set(graphrag_scores))

    return {
        "vector": vector_scores,
        "graphrag": graphrag_scores,
        "delta": {
            metric: round(graphrag_scores.get(metric, 0.0) - vector_scores.get(metric, 0.0), 4)
            for metric in metrics
        },
    }


def summarize_ragas_result(result: Any) -> dict[str, float]:
    """Normalize RAGAS result objects into mean metric scores."""
    if hasattr(result, "to_pandas"):
        dataframe = result.to_pandas()
        scores: dict[str, float] = {}
        for column in dataframe.columns:
            values = [
                float(value)
                for value in dataframe[column].tolist()
                if isinstance(value, (int, float)) and value == value
            ]
            if values:
                scores[str(column)] = round(mean(values), 4)
        return scores

    if isinstance(result, dict):
        return {
            str(key): round(float(value), 4)
            for key, value in result.items()
            if isinstance(value, (int, float))
        }

    scores = getattr(result, "scores", None)
    if isinstance(scores, list):
        by_metric: dict[str, list[float]] = {}
        for row in scores:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    by_metric.setdefault(str(key), []).append(float(value))
        return {key: round(mean(values), 4) for key, values in by_metric.items()}

    raise TypeError(f"Unsupported RAGAS result type: {type(result)!r}")


def _chunk_texts(chunks: list[dict[str, Any]]) -> list[str]:
    return [str(chunk["text"]) for chunk in chunks if chunk.get("text")]

