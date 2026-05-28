"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ── Auth ─────────────────────────────────────────────

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
    password_changed:bool = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool
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


# ── Chat ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[str] = None


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


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: List[SourceChunk] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    document_id: Optional[str] = None


# Rebuild models for forward references
TokenResponse.model_rebuild()
