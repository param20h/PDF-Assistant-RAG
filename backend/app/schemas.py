"""
Pydantic schemas for API request/response validation.
"""
import json
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from app.models import UserRole, WorkspaceRole
from app.password_validation import validate_password


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorEnvelope


class ValidationErrorResponse(BaseModel):
    error: ErrorEnvelope


# ── Auth ─────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class RegistrationResponse(MessageResponse):
    email: EmailStr
    verification_url: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username:Optional[str] = None

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
class UserUpdateResponse(BaseModel):
    id: str
    username: str
    email: EmailStr

class UpdatePassword(BaseModel):
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value

class UpdatePasswordResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    password_changed: bool = True

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value    


class WorkspaceInviteRequest(BaseModel):
    email: EmailStr
    workspace_name: str = Field(..., min_length=1, max_length=100)
    message: Optional[str] = None


class WorkspaceInviteResponse(BaseModel):
    email: EmailStr
    workspace_name: str
    invite_link: str
    expires_in_hours: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class HFTokenUpdate(BaseModel):
    hf_token: str = Field(..., min_length=1, max_length=500)


class GoogleDriveAuthUrlResponse(BaseModel):
    auth_url: str


class GoogleDriveStatusResponse(BaseModel):
    connected: bool


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_preview: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key_preview: str
    created_at: datetime
    raw_key: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_admin: bool
    is_verified: bool
    hf_token: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Documents ────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    original_name: str = "Untitled Document"
    file_size: int = 0
    page_count: int = 0
    chunk_count: int = 0
    status: str = "pending"
    error_message: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    summary: Optional[str] = None
    task_id: Optional[str] = None
    keywords: Optional[List[str]] = []
    extracted_urls: Optional[List[str]] = []

    @field_validator("id", mode="before")
    @classmethod
    def parse_id(cls, v):
        return str(v) if v is not None else ""

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return []

    @field_validator("extracted_urls", mode="before")
    @classmethod
    def parse_extracted_urls(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return []


    class Config:
        from_attributes = True

class BatchUploadResponse(BaseModel):
    documents: List[DocumentResponse]
    task_ids: List[str]
    total: int
    failed: List[str] = []

class DocumentRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Document name cannot be empty")
        return stripped


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata via PATCH. All fields are optional
    so that callers can send a partial update (e.g. only the name or only the
    summary) without having to include every field."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = Field(None, max_length=5000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Document name cannot be empty")
            return stripped
        return value


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    page_count: int
    chunk_count: int
    error_message: Optional[str] = None
    processing_progress: Optional[int] = None
    processing_stage: Optional[str] = None
    retry_count: Optional[int] = None
    last_error_traceback: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse] = []
    total: int = 0
    page: int = 1
    pages: int = 1
    total_pages: int = 1
    limit: int = 20
    query: Optional[str] = None


# Admin

class DiskUsageResponse(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
    upload_dir_bytes: int


class AdminStatsResponse(BaseModel):
    total_users: int
    total_pdfs_uploaded: int
    total_documents: int
    total_messages: int
    average_query_response_time_ms: float
    query_count: int
    disk_space_usage: DiskUsageResponse
    users: List[UserResponse]


# ── Chat ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    session_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Strip control characters (null bytes, ANSI escapes, etc.) from user input."""
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        stripped = cleaned.strip()
        if not stripped:
            raise ValueError("Question cannot be empty after sanitization")
        return stripped


class SourceChunk(BaseModel):
    text: str
    filename: str
    page: int
    score: float
    confidence: float
    bbox: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []
    document_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    feedback: Optional[str] = Field(None, pattern="^(up|down)?$")


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[SourceChunk] = []
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    document_id: Optional[str] = None

# Chunk settings schema for optional chunk size and overlap parameters in document processing
class ChunkSettings(BaseModel):
    chunk_size: int = Field(default=1000, ge=100, le=2000)
    chunk_overlap: int = Field(default=200, ge=0)

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        if "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v

class UploadUrl(BaseModel):
    url: str

class ShareAnswerResponse(BaseModel):
    id: str
    content: str
    sources: List[SourceChunk] = []
    created_at: datetime


class ShareLinkResponse(BaseModel):
    message_id: str
    share_url: str


class FeedbackRequest(BaseModel):
    feedback: Optional[str] = Field(None, pattern="^(up|down)?$")


# ── Chat Session ──────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class ChatSessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Workspaces ────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    joined_at: datetime

    class Config:
        from_attributes = True


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceDetailResponse(BaseModel):
    """Workspace detail including the full member list."""
    id: str
    name: str
    created_by: str
    created_at: datetime
    members: List[WorkspaceMemberResponse] = []

    class Config:
        from_attributes = True


class WorkspaceMemberAdd(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: WorkspaceRole = WorkspaceRole.viewer


class WorkspaceMemberRoleUpdate(BaseModel):
    role: WorkspaceRole


# Rebuild models for forward references
TokenResponse.model_rebuild()
