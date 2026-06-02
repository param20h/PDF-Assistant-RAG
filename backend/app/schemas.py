"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models import UserRole


# ── Auth ─────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username:Optional[str] = None

class UserUpdateResponse(BaseModel):
    id: str
    username: str
    email: EmailStr

class UpdatePassword(BaseModel):
    password: str
    confirm_password: str

class UpdatePasswordResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    password_changed: bool = True


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
    """Request schema for updating the user's HuggingFace token."""
    hf_token: str


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
    hf_token: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Documents ────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    original_name: str
    file_size: int
    page_count: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: datetime
    summary: Optional[str] = None # New field for document summary

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    page_count: int
    chunk_count: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    pages: int


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


class SourceChunk(BaseModel):
    text: str
    filename: str
    page: int
    score: float
    confidence: float


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
    chunk_size: int | None
    chunk_overlap: int | None
      
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


# ── Chat Session ──────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


# Rebuild models for forward references
TokenResponse.model_rebuild()
