"""
SQLAlchemy ORM models for users, documents, and chat messages.
"""
import uuid
import enum
import base64
import hashlib
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value if dialect.name == 'postgresql' else str(value)
        try:
            val_uuid = uuid.UUID(value)
            return val_uuid if dialect.name == 'postgresql' else str(val_uuid)
        except ValueError:
            if dialect.name == 'postgresql':
                return uuid.UUID(int=0)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


class EncryptedString(TypeDecorator):
    """
    A custom SQLAlchemy type that transparently encrypts strings in the database 
    using Fernet (AES). This ensures sensitive tokens aren't stored in plain text 
    while remaining easily accessible in code.
    """
    impl = Text
    cache_ok = False

    def _get_cipher(self):
        from app.config import get_settings
        settings = get_settings()
        # Derive a 32-byte key from the SECRET_KEY for Fernet encryption
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        return Fernet(key)

    def process_bind_param(self, value, dialect):
        """Encrypt the value before saving to the database."""
        if value is None:
            return value
        cipher = self._get_cipher()
        return cipher.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        """Decrypt the value after reading from the database."""
        if value is None:
            return value
        cipher = self._get_cipher()
        try:
            return cipher.decrypt(value.encode()).decode()
        except Exception:
            # Fallback for unencrypted data or if decryption fails
            return value


class UserRole(str, enum.Enum):
    """
    Defines the available user roles for Role-Based Access Control (RBAC).
    - 'admin': Full access to system statistics and user management.
    - 'user': Standard access for uploading and chatting with documents.
    """
    user = "user"
    admin = "admin"


class User(Base):
    """
    Represents a registered user within the system.
    Supports both legacy 'is_admin' flags and the modern 'role' enum for permissions.
    """
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Permission fields: transitioning towards 'role', keeping 'is_admin' for compatibility
    role = Column(
        SQLAlchemyEnum(UserRole),
        default=UserRole.user,
        nullable=False,
        server_default="user"
    )
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True, index=True)
    hf_token = Column(EncryptedString, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """
    Stores secure hashes of API keys used for programmatic interaction with the system.
    """
    __tablename__ = "api_keys"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)
    hashed_key = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class ChatSession(Base):
    """
    Groups chat messages into logical sessions/threads.
    """
    __tablename__ = "chat_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class Document(Base):
    """
    Metadata and processing status for files uploaded by users.
    """
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)        # Stored filename (UUID-based)
    original_name = Column(String(255), nullable=False)    # User's original filename
    file_size = Column(Integer, default=0)                 # Size in bytes
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")          # pending | processing | ready | failed
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)
    summary = Column(Text, nullable=True)  # Optional summary of the document's content

    # Relationships
    owner = relationship("User", back_populates="documents")
    messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")


class ChatMessage(Base):
    """
    Persistent log of conversations between users and the AI analyst.
    """
    __tablename__ = "chat_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(GUID, ForeignKey("documents.id"), nullable=True, index=True)
    session_id = Column(GUID, ForeignKey("chat_sessions.id"), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)  # JSON representation of retrieved sources
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="messages")
    document = relationship("Document", back_populates="messages")
    session = relationship("ChatSession", back_populates="messages")
    shared_message = relationship("SharedMessage", back_populates="message", uselist=False, cascade="all, delete-orphan")


class DriveConnection(Base):
    __tablename__ = "drive_connections"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    folder_id = Column(String(255), nullable=False, index=True)
    credentials_json = Column(Text, nullable=True)
    service_account_file = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="drive_connections")


class SharedMessage(Base):
    """
    Links specific chat messages to public sharing URLs.
    """
    __tablename__ = "shared_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    message_id = Column(GUID, ForeignKey("chat_messages.id"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    message = relationship("ChatMessage", back_populates="shared_message")
