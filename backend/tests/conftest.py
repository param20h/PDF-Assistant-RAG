import os
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
os.environ["DATABASE_URL"] = "sqlite:///./test_bootstrap.db"
os.environ["DEBUG"] = "false"
os.environ["HF_TOKEN"] = "test-hf-token"
os.environ["UPLOAD_DIR"] = str(ROOT / "backend" / "test_uploads")
os.environ["CHROMA_PERSIST_DIR"] = str(ROOT / "backend" / "test_chroma")


fake_embeddings = types.ModuleType("app.rag.embeddings")
fake_embeddings.get_embedding_model = lambda: object()
fake_embeddings.embed_query = lambda query: [0.0]
fake_embeddings.embed_texts = lambda texts: [[0.0] for _ in texts]
sys.modules.setdefault("app.rag.embeddings", fake_embeddings)


class _FakeChromaClient:
    def heartbeat(self):
        return "ok"


fake_vectorstore = types.ModuleType("app.rag.vectorstore")
fake_vectorstore.get_chroma_client = lambda: _FakeChromaClient()
fake_vectorstore.store_chunks = lambda chunks, document_id, filename, user_id: len(chunks)
fake_vectorstore.delete_document_chunks = lambda document_id, user_id: None
fake_vectorstore.query_chunks = lambda query_embedding, user_id, document_id=None, top_k=10: []
sys.modules.setdefault("app.rag.vectorstore", fake_vectorstore)

slowapi_module = types.ModuleType("slowapi")
slowapi_errors = types.ModuleType("slowapi.errors")
slowapi_middleware = types.ModuleType("slowapi.middleware")
slowapi_util = types.ModuleType("slowapi.util")


class RateLimitExceeded(Exception):
    pass


class SlowAPIMiddleware:
    def __init__(self, app, *args, **kwargs):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


class Limiter:
    def __init__(self, key_func=None, *args, **kwargs):
        self.key_func = key_func

    def limit(self, _value):
        def decorator(fn):
            return fn
        return decorator


slowapi_errors.RateLimitExceeded = RateLimitExceeded
slowapi_middleware.SlowAPIMiddleware = SlowAPIMiddleware
slowapi_util.get_remote_address = lambda request: "127.0.0.1"
slowapi_module.Limiter = Limiter

sys.modules.setdefault("slowapi", slowapi_module)
sys.modules.setdefault("slowapi.errors", slowapi_errors)
sys.modules.setdefault("slowapi.middleware", slowapi_middleware)
sys.modules.setdefault("slowapi.util", slowapi_util)

from app.auth import create_access_token, create_refresh_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import ChatMessage, Document, User


@pytest.fixture()
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    @asynccontextmanager
    async def no_lifespan(_app):
        yield

    monkeypatch.setattr("app.database.SessionLocal", lambda: db_session)
    app.dependency_overrides[get_db] = override_get_db
    app.router.lifespan_context = no_lifespan

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def user(db_session):
    instance = User(
        username="tester",
        email="tester@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def other_user(db_session):
    instance = User(
        username="other",
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def refresh_token(user):
    return create_refresh_token(user.id)


@pytest.fixture()
def ready_document(db_session, user):
    instance = Document(
        user_id=user.id,
        filename="ready.txt",
        original_name="ready.txt",
        file_size=128,
        page_count=1,
        chunk_count=2,
        status="ready",
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def pending_document(db_session, user):
    instance = Document(
        user_id=user.id,
        filename="pending.txt",
        original_name="pending.txt",
        file_size=64,
        status="pending",
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def assistant_message(db_session, user):
    instance = ChatMessage(
        user_id=user.id,
        role="assistant",
        content="Shared assistant answer",
        sources_json='[{"text":"Source text","filename":"file.txt","page":1,"score":0.9,"confidence":95.0}]',
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def user_message(db_session, user):
    instance = ChatMessage(
        user_id=user.id,
        role="user",
        content="Private user prompt",
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture()
def other_user_assistant_message(db_session, other_user):
    instance = ChatMessage(
        user_id=other_user.id,
        role="assistant",
        content="Other user's answer",
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance
