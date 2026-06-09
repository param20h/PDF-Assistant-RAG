from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid

from app.database import get_db
from app.exceptions import ValidationException, NotFoundException
from app.models import User
from app.schemas import UserProfileUpdate, UserResponse
from app.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])

UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/", response_model=UserResponse)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.username:
        current_user.username = payload.username

    if payload.display_name:
        current_user.display_name = payload.display_name

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed_extensions = [".png", ".jpg", ".jpeg"]

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise ValidationException("Invalid image format")

    filename = f"{uuid.uuid4()}{extension}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.avatar_url = f"/uploads/avatars/{filename}"

    db.commit()
    db.refresh(current_user)

    return current_user