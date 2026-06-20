"""Regression tests for backend/app/services/cleanup.py.

Covers GH issue: cleanup jobs silently skip eligible documents because the
old implementation tracked a manually advancing ``offset`` across batches
inside one long-lived transaction. These tests seed more than one batch's
worth of eligible rows (``_CLEANUP_BATCH_SIZE`` is 100) and assert that a
single call to each cleanup function processes *all* of them, in a stable
order, and that partial failures don't roll back already-committed batches.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Document
from app.services import cleanup as cleanup_mod
from app.services.cleanup import _CLEANUP_BATCH_SIZE


SEEDED_ROWS = _CLEANUP_BATCH_SIZE * 2 + 50  # 250 with the current batch size of 100


def _seed_stale_processing_documents(db_session, user, count, cutoff):
    docs = []
    for i in range(count):
        doc = Document(
            user_id=user.id,
            filename=f"stale_{i}.txt",
            original_name=f"stale_{i}.txt",
            status="processing",
            processing_started_at=cutoff - timedelta(minutes=1),
            is_deleted=False,
        )
        db_session.add(doc)
        docs.append(doc)
    db_session.commit()
    return docs


def _seed_old_deleted_documents(db_session, user, count, cutoff):
    docs = []
    for i in range(count):
        doc = Document(
            user_id=user.id,
            filename=f"deleted_{i}.txt",
            original_name=f"deleted_{i}.txt",
            status="ready",
            is_deleted=True,
            deleted_at=cutoff - timedelta(days=1),
        )
        db_session.add(doc)
        docs.append(doc)
    db_session.commit()
    return docs


def _seed_inactive_documents(db_session, user, count, cutoff):
    docs = []
    for i in range(count):
        doc = Document(
            user_id=user.id,
            filename=f"inactive_{i}.txt",
            original_name=f"inactive_{i}.txt",
            status="ready",
            is_deleted=False,
            last_accessed_at=cutoff - timedelta(days=1),
        )
        db_session.add(doc)
        docs.append(doc)
    db_session.commit()
    return docs


@pytest.fixture()
def patch_session_local(monkeypatch, db_session):
    """Route app.database.SessionLocal() (used inside get_db_session) to the
    test's single in-memory db_session, matching the pattern already used by
    the `client` fixture in conftest.py.
    """
    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)


@pytest.fixture()
def stub_vectorstore(monkeypatch):
    """Stub out the vectorstore delete used by _hard_delete_document so hard
    deletes don't depend on a real Chroma instance.
    """
    monkeypatch.setattr(
        "app.rag.vectorstore.delete_document_chunks",
        lambda document_id, user_id: None,
    )


def test_cleanup_stale_documents_processes_all_rows_across_multiple_batches(
    db_session, user, patch_session_local
):
    """A single call must mark *every* eligible stale document as failed,
    not just the first batch's worth. With the old offset-tracking loop on
    a single uncommitted transaction this assertion still happened to pass
    on SQLite/autoflush=False, but the (now removed) offset arithmetic was
    still wrong for any backend where each batch is visible to the next
    query (e.g. once batches are committed independently, as they are now).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=30
    )  # default DOC_PROCESSING_TIMEOUT_MINUTES
    _seed_stale_processing_documents(db_session, user, SEEDED_ROWS, cutoff)

    total = cleanup_mod.cleanup_stale_documents()

    assert total == SEEDED_ROWS
    remaining_processing = (
        db_session.query(Document).filter(Document.status == "processing").count()
    )
    failed_count = db_session.query(Document).filter(Document.status == "failed").count()
    assert remaining_processing == 0
    assert failed_count == SEEDED_ROWS


def test_cleanup_old_deleted_documents_processes_all_rows_across_multiple_batches(
    db_session, user, patch_session_local, stub_vectorstore
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)  # default DOC_CLEANUP_MAX_AGE_DAYS
    _seed_old_deleted_documents(db_session, user, SEEDED_ROWS, cutoff)

    total = cleanup_mod.cleanup_old_deleted_documents()

    assert total == SEEDED_ROWS
    assert db_session.query(Document).count() == 0


def test_cleanup_inactive_active_documents_processes_all_rows_across_multiple_batches(
    db_session, user, patch_session_local, stub_vectorstore
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)  # default DOC_CLEANUP_INACTIVE_DAYS
    _seed_inactive_documents(db_session, user, SEEDED_ROWS, cutoff)

    total = cleanup_mod.cleanup_inactive_active_documents()

    assert total == SEEDED_ROWS
    assert db_session.query(Document).count() == 0


def test_cleanup_old_deleted_documents_preserves_earlier_committed_batches_on_failure(
    db_session, user, patch_session_local, stub_vectorstore, monkeypatch
):
    """If processing fails partway through a large job, batches that were
    already committed must stay committed -- a failure on document #220
    (well inside the third batch) must not roll back the 200 documents
    purged in the first two batches. This is the corruption scenario the
    old single-long-transaction-per-job implementation was vulnerable to:
    a single unhandled error anywhere in the loop discarded every prior
    batch's work in that call, even though irreversible side effects (the
    vector-store deletes already performed for those rows) had already
    happened.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    _seed_old_deleted_documents(db_session, user, SEEDED_ROWS, cutoff)

    call_count = {"n": 0}
    original = cleanup_mod._hard_delete_document

    def flaky_hard_delete(db, doc):
        call_count["n"] += 1
        if call_count["n"] == 220:
            raise RuntimeError("simulated unhandled failure mid-job")
        return original(db, doc)

    monkeypatch.setattr(cleanup_mod, "_hard_delete_document", flaky_hard_delete)

    with pytest.raises(RuntimeError):
        cleanup_mod.cleanup_old_deleted_documents()

    # Batches 1 and 2 (200 rows) were committed before the failure in batch 3;
    # only the still-uncommitted remainder (50 rows) should survive.
    remaining = db_session.query(Document).count()
    assert remaining == SEEDED_ROWS - 200


def test_cleanup_inactive_documents_disabled_returns_without_querying(
    db_session, user, patch_session_local, monkeypatch
):
    monkeypatch.setattr(cleanup_mod.settings, "DOC_CLEANUP_ENABLED", False)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    _seed_inactive_documents(db_session, user, 5, cutoff)

    total = cleanup_mod.cleanup_inactive_active_documents()

    assert total == 0
    assert db_session.query(Document).count() == 5