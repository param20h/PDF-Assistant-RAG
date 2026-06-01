"""
Admin-only operational statistics routes.
"""
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.metrics import get_query_metrics
from app.models import Document, User, ChatMessage
from app.schemas import AdminStatsResponse, DiskUsageResponse, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0

    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get admin dashboard statistics",
    description=(
        "Returns aggregate user, document, message, query-latency, and disk "
        "usage metrics for authenticated administrators."
    ),
)
def get_admin_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return aggregate operational statistics for the admin dashboard.

    The response includes counts for users, uploaded PDFs, all documents, chat
    messages, average RAG query latency, and upload-directory disk usage.
    Access is restricted by the `get_current_admin` dependency.
    """
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    disk_usage = shutil.disk_usage(upload_dir)
    used_percent = (
        round((disk_usage.used / disk_usage.total) * 100, 2)
        if disk_usage.total
        else 0.0
    )
    query_metrics = get_query_metrics()

    total_pdfs_uploaded = (
        db.query(Document)
        .filter(func.lower(Document.original_name).like("%.pdf"))
        .count()
    )

    return AdminStatsResponse(
        total_users=db.query(User).count(),
        total_pdfs_uploaded=total_pdfs_uploaded,
        total_documents=db.query(Document).count(),
        total_messages=db.query(ChatMessage).count(),
        average_query_response_time_ms=float(
            query_metrics["average_query_response_time_ms"]
        ),
        query_count=int(query_metrics["query_count"]),
        disk_space_usage=DiskUsageResponse(
            total_bytes=disk_usage.total,
            used_bytes=disk_usage.used,
            free_bytes=disk_usage.free,
            usage_percent=used_percent,
            upload_dir_bytes=_directory_size(upload_dir),
        ),
        users=db.query(User).all()
    )


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all registered users",
    description="Returns the registered user inventory for authenticated administrators.",
)
def list_all_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """List all registered users.

    Access is restricted to administrators and the response is serialized
    through `UserResponse` so token fields and secrets are not exposed.
    """
    return db.query(User).all()
