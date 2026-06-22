import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Document, User
from app.rag.graph_builder import load_graph

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
logger = logging.getLogger(__name__)


# ── Response schemas ──────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    name: str
    label: str          # NER type, e.g. "PERSON", "ORG", "GPE"
    mentions: int
    pages: List[int]


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int
    pages: List[int]


class GraphResponse(BaseModel):
    document_id: str
    document_name: str
    node_count: int
    edge_count: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphSummaryResponse(BaseModel):
    document_id: str
    document_name: str
    node_count: int
    edge_count: int
    top_entities: List[Dict[str, Any]]
    graph_available: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_owned_document(document_id: str, user: User, db: Session) -> Document:
    """Return the document if it exists and belongs to the current user."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{document_id}", response_model=GraphResponse)
def get_graph(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the full knowledge graph (nodes + edges) for a document.

    The graph is built by ``graph_builder.py`` during ingestion and stored as
    a JSON file on disk.  If the graph file does not exist yet (document still
    processing, or graph extraction was skipped) a 404 is returned so the
    frontend can show an appropriate empty state.
    """
    doc = _get_owned_document(document_id, current_user, db)

    graph = load_graph(str(current_user.id), document_id)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge graph not available for this document yet. "
                   "The document may still be processing.",
        )

    nodes: List[GraphNode] = []
    for node_id, data in graph.nodes(data=True):
        nodes.append(
            GraphNode(
                id=node_id,
                name=data.get("name", node_id),
                label=data.get("label", "UNKNOWN"),
                mentions=data.get("mentions", 1),
                pages=sorted(data.get("pages", [])),
            )
        )

    edges: List[GraphEdge] = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            GraphEdge(
                source=source,
                target=target,
                weight=data.get("weight", 1),
                pages=sorted(data.get("pages", [])),
            )
        )

    return GraphResponse(
        document_id=document_id,
        document_name=doc.original_name,
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        nodes=nodes,
        edges=edges,
    )


@router.get("/{document_id}/summary", response_model=GraphSummaryResponse)
def get_graph_summary(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return lightweight graph statistics without the full node/edge payload.

    Useful for deciding whether to show the graph toggle button in the UI.
    """
    doc = _get_owned_document(document_id, current_user, db)

    graph = load_graph(str(current_user.id), document_id)
    if graph is None:
        return GraphSummaryResponse(
            document_id=document_id,
            document_name=doc.original_name,
            node_count=0,
            edge_count=0,
            top_entities=[],
            graph_available=False,
        )

    # Top 10 nodes by mention count
    top_entities = sorted(
        [
            {
                "id": node_id,
                "name": data.get("name", node_id),
                "label": data.get("label", "UNKNOWN"),
                "mentions": data.get("mentions", 1),
            }
            for node_id, data in graph.nodes(data=True)
        ],
        key=lambda x: x["mentions"],
        reverse=True,
    )[:10]

    return GraphSummaryResponse(
        document_id=document_id,
        document_name=doc.original_name,
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        top_entities=top_entities,
        graph_available=True,
    )
