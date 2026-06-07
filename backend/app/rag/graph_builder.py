"""
Knowledge graph construction and persistence for GraphRAG.
"""
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import networkx as nx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_nlp = None


@dataclass(frozen=True)
class Entity:
    id: str
    text: str
    label: str


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "unknown"


def get_graph_path(user_id: str, document_id: str) -> Path:
    """Return the on-disk graph path for one user/document pair."""
    filename = f"{_safe_id(user_id)}_{_safe_id(document_id)}.json"
    return Path(settings.GRAPH_PERSIST_DIR) / filename


def iter_graph_paths(user_id: str) -> Iterable[Path]:
    """Yield every persisted graph path for a user."""
    graph_dir = Path(settings.GRAPH_PERSIST_DIR)
    if not graph_dir.exists():
        return []

    prefix = f"{_safe_id(user_id)}_"
    return sorted(graph_dir.glob(f"{prefix}*.json"))


def _get_nlp():
    """Load the spaCy English NER model lazily."""
    global _nlp
    if _nlp is None:
        import spacy

        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' is required for GraphRAG entity extraction. "
                "Install it with: python -m spacy download en_core_web_sm"
            ) from exc
    return _nlp


def _entity_id(text: str, label: str) -> str:
    normalized = " ".join(text.split()).casefold()
    return f"{label}:{normalized}"


def extract_entities(text: str) -> List[Entity]:
    """Extract configured named entities from text."""
    if not text or not text.strip():
        return []

    doc = _get_nlp()(text)
    entities: Dict[str, Entity] = {}

    for ent in doc.ents:
        value = " ".join(ent.text.split()).strip()
        if not value or ent.label_ not in settings.GRAPH_ENTITY_LABELS:
            continue

        entity_id = _entity_id(value, ent.label_)
        entities.setdefault(
            entity_id,
            Entity(id=entity_id, text=value, label=ent.label_),
        )

    return list(entities.values())


def build_graph(chunks: List[Dict[str, Any]]) -> nx.Graph:
    """Build an entity co-occurrence graph from document chunks."""
    graph = nx.Graph()

    for chunk in chunks:
        text = chunk.get("text", "")
        page = chunk.get("page")
        chunk_index = chunk.get("chunk_index")
        entities = extract_entities(text)

        for entity in entities:
            if graph.has_node(entity.id):
                graph.nodes[entity.id]["mentions"] += 1
                graph.nodes[entity.id]["pages"].add(page)
                graph.nodes[entity.id]["chunks"].add(chunk_index)
            else:
                graph.add_node(
                    entity.id,
                    name=entity.text,
                    label=entity.label,
                    mentions=1,
                    pages={page},
                    chunks={chunk_index},
                )

        for left_index, left in enumerate(entities):
            for right in entities[left_index + 1:]:
                if graph.has_edge(left.id, right.id):
                    graph[left.id][right.id]["weight"] += 1
                    graph[left.id][right.id]["pages"].add(page)
                    graph[left.id][right.id]["chunks"].add(chunk_index)
                else:
                    graph.add_edge(
                        left.id,
                        right.id,
                        weight=1,
                        pages={page},
                        chunks={chunk_index},
                    )

    _convert_sets_for_json(graph)
    return graph


def _convert_sets_for_json(graph: nx.Graph) -> None:
    for _, data in graph.nodes(data=True):
        data["pages"] = sorted(item for item in data.get("pages", []) if item is not None)
        data["chunks"] = sorted(item for item in data.get("chunks", []) if item is not None)

    for _, _, data in graph.edges(data=True):
        data["pages"] = sorted(item for item in data.get("pages", []) if item is not None)
        data["chunks"] = sorted(item for item in data.get("chunks", []) if item is not None)


def save_graph(graph: nx.Graph, user_id: str, document_id: str) -> Path:
    """Persist a graph to disk as node-link JSON."""
    graph_path = get_graph_path(user_id, document_id)
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    data = nx.node_link_data(graph)
    data["metadata"] = {
        "user_id": user_id,
        "document_id": document_id,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
    }

    graph_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    logger.info(
        "Saved knowledge graph for document %s with %s nodes and %s edges",
        document_id,
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    return graph_path


def load_graph(user_id: str, document_id: str) -> Optional[nx.Graph]:
    """Load a persisted graph for one user/document pair."""
    return load_graph_path(get_graph_path(user_id, document_id))


def load_graph_path(graph_path: Path) -> Optional[nx.Graph]:
    """Load a graph from a concrete JSON path."""
    if not graph_path.exists():
        return None

    data = json.loads(graph_path.read_text(encoding="utf-8"))
    return nx.node_link_graph(data)


def delete_graph(user_id: str, document_id: str) -> None:
    """Delete a persisted graph file if it exists."""
    get_graph_path(user_id, document_id).unlink(missing_ok=True)
