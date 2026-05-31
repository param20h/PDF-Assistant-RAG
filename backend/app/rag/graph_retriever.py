"""
Knowledge graph retrieval for augmenting RAG context.
"""
import logging
from typing import Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx

from app.config import get_settings
from app.rag.graph_builder import (
    extract_entities,
    iter_graph_paths,
    load_graph,
    load_graph_path,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _candidate_graphs(user_id: str, document_id: Optional[str]) -> Iterable[nx.Graph]:
    if document_id:
        graph = load_graph(user_id, document_id)
        return [graph] if graph is not None else []

    graphs = []
    for path in iter_graph_paths(user_id):
        graph = load_graph_path(path)
        if graph is not None:
            graphs.append(graph)
    return graphs


def _node_name(graph: nx.Graph, node_id: str) -> str:
    return graph.nodes[node_id].get("name", node_id.split(":", 1)[-1])


def _match_query_nodes(graph: nx.Graph, query: str) -> Set[str]:
    query_entities = extract_entities(query)
    matched = {entity.id for entity in query_entities if graph.has_node(entity.id)}

    if matched:
        return matched

    query_text = query.casefold()
    for node_id, data in graph.nodes(data=True):
        name = data.get("name", "").casefold()
        if name and name in query_text:
            matched.add(node_id)

    return matched


def _format_pages(pages: List[int]) -> str:
    if not pages:
        return "unknown pages"
    if len(pages) == 1:
        return f"page {pages[0]}"
    return "pages " + ", ".join(str(page) for page in pages[:4])


def _relationship_key(left: str, right: str) -> Tuple[str, str]:
    return tuple(sorted((left, right)))


def get_entity_context(
    query: str,
    user_id: str,
    document_id: Optional[str] = None,
) -> str:
    """Return compact graph relationship context relevant to the query."""
    relationships: Dict[Tuple[str, str], Dict[str, object]] = {}

    try:
        graphs = _candidate_graphs(user_id=user_id, document_id=document_id)
        for graph in graphs:
            matched_nodes = _match_query_nodes(graph, query)

            for node_id in matched_nodes:
                neighbors = sorted(
                    graph.neighbors(node_id),
                    key=lambda neighbor: graph[node_id][neighbor].get("weight", 0),
                    reverse=True,
                )
                for neighbor_id in neighbors:
                    edge = graph[node_id][neighbor_id]
                    left = _node_name(graph, node_id)
                    right = _node_name(graph, neighbor_id)
                    key = _relationship_key(left.casefold(), right.casefold())
                    existing = relationships.setdefault(
                        key,
                        {
                            "left": left,
                            "right": right,
                            "weight": 0,
                            "pages": set(),
                        },
                    )
                    existing["weight"] = int(existing["weight"]) + int(edge.get("weight", 1))
                    existing["pages"].update(edge.get("pages", []))
    except Exception as exc:
        logger.warning("GraphRAG context retrieval failed: %s", exc)
        return ""

    if not relationships:
        return ""

    ranked = sorted(
        relationships.values(),
        key=lambda item: int(item["weight"]),
        reverse=True,
    )[: settings.GRAPH_MAX_RELATIONSHIPS]

    lines = ["## Knowledge Graph Context"]
    for item in ranked:
        pages = sorted(item["pages"])
        lines.append(
            f"- {item['left']} is related to {item['right']} "
            f"through document co-occurrence on {_format_pages(pages)} "
            f"(strength: {item['weight']})."
        )

    return "\n".join(lines)
