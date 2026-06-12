"""
Admin-only operational statistics and database maintenance routes.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, text, inspect
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
    """Return aggregate operational statistics for the admin dashboard."""
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
    """List all registered users."""
    return db.query(User).all()


@router.get(
    "/export-db",
    summary="Export database backup",
    description="Dumps all database tables securely into either a JSON document or a SQL injection script.",
)
def export_database(
    format: str = "json",
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Securely export all database table records for offsite backup support."""
    format_type = format.lower()
    if format_type not in ["json", "sql"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid export format specified. Supported variants: json, sql"
        )

    # Inspect schema names dynamically from current environment binding context
    inspector = inspect(db.get_bind())
    table_names = inspector.get_table_names()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if format_type == "json":
        backup_data = {}
        for table in table_names:
            result = db.execute(text(f"SELECT * FROM {table}"))
            columns = list(result.keys())
            rows = []
            for row in result.fetchall():
                row_dict = {}
                for col, val in zip(columns, row):
                    if isinstance(val, (datetime, datetime.date)):
                        row_dict[col] = val.isoformat()
                    elif isinstance(val, bytes):
                        row_dict[col] = val.decode("utf-8", errors="ignore")
                    else:
                        row_dict[col] = val
                rows.append(row_dict)
            backup_data[table] = rows

        content = json.dumps(backup_data, indent=2, default=str)
        filename = f"db_backup_{timestamp}.json"
        media_type = "application/json"

    else:
        # SQL Injection Script Generation
        sql_lines = [
            "-- Enterprise Agentic RAG System Database Backup",
            f"-- Generated at: {datetime.now(timezone.utc).isoformat()}",
            "-- Format: cross-compatible SQL script\n"
        ]
        for table in table_names:
            result = db.execute(text(f"SELECT * FROM {table}"))
            columns = list(result.keys())
            rows = result.fetchall()
            if rows:
                sql_lines.append(f"-- Data records for table: {table}")
                cols_str = ", ".join([f'"{c}"' for c in columns])
                for row in rows:
                    vals = []
                    for val in row:
                        if val is None:
                            vals.append("NULL")
                        elif isinstance(val, (int, float)):
                            vals.append(str(val))
                        elif isinstance(val, bool):
                            vals.append("1" if val else "0")
                        elif isinstance(val, (datetime, datetime.date)):
                            vals.append(f"'{val.isoformat()}'")
                        else:
                            escaped_val = str(val).replace("'", "''")
                            vals.append(f"'{escaped_val}'")
                    vals_str = ", ".join(vals)
                    sql_lines.append(f'INSERT INTO "{table}" ({cols_str}) VALUES ({vals_str});')
                sql_lines.append("")

        content = "\n".join(sql_lines)
        filename = f"db_backup_{timestamp}.sql"
        media_type = "application/sql"

    # Enforce strict security standard response headers
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
    }
    return Response(content=content, media_type=media_type, headers=headers)
