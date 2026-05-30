"""
SQLAlchemy ORM models for users, documents, and chat messages.
"""
import uuid
import base64
import hashlib
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from app.database import Base


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator that encrypts strings before storing in database,
    and decrypts them when reading.
    """
    impl = Text
    cache_ok = False

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        from app.config import get_settings
        settings = get_settings()
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        cipher = Fernet(key)
        return cipher.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        from app.config import get_settings
        settings = get_settings()
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        cipher = Fernet(key)
        try:
            return cipher.decrypt(value.encode()).decode()
        except Exception:
            return value


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True, index=True)
    hf_token = Column(EncryptedString, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)
    hashed_key = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)        # Stored filename (UUID-based)
    original_name = Column(String(255), nullable=False)    # User's original filename
    file_size = Column(Integer, default=0)                 # Size in bytes
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")         # pending | processing | ready | failed
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    summary = Column(Text, nullable=True)  # Optional summary of the document's content

    # Relationships
    owner = relationship("User", back_populates="documents")
    messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)  # JSON string of source citations
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="messages")
    document = relationship("Document", back_populates="messages")
    shared_message = relationship("SharedMessage", back_populates="message", uselist=False, cascade="all, delete-orphan")


class SharedMessage(Base):
    __tablename__ = "shared_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("chat_messages.id"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    message = relationship("ChatMessage", back_populates="shared_message")
