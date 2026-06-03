"""Run a 50-question RAGAS comparison for vector search and GraphRAG."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_DATASET = BACKEND_DIR / "evaluation" / "ragas_sample_questions.jsonl"
DEFAULT_OUTPUT = BACKEND_DIR / "evaluation" / "ragas_results.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate vector search versus GraphRAG with RAGAS.",
    )
    parser.add_argument("--user-id", required=True, help="Owner user id for indexed documents.")
    parser.add_argument("--document-id", help="Optional single document id to evaluate.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from app.evaluation.ragas_pipeline import collect_records, compare_pipelines, load_questions

    questions = load_questions(args.dataset, limit=args.limit)
    grouped_records = collect_records(
        questions=questions,
        user_id=args.user_id,
        document_id=args.document_id,
    )
    scores = compare_pipelines(grouped_records)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset),
        "question_count": len(questions),
        "user_id": args.user_id,
        "document_id": args.document_id,
        "scores": scores,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["scores"], indent=2))
    print(f"Wrote RAGAS evaluation results to {args.output}")


if __name__ == "__main__":
    main()
