from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    credits: int

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProjectCreateRequest(BaseModel):
    title: str
    type: str = "SCRIPT"
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    type: str
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ScriptGenerateRequest(BaseModel):
    topic: str
    language: str = "ar"
    style: str = "educational"
    duration: int = 60
    project_id: Optional[str] = None
    content_type: str = "general"


class ScriptResponse(BaseModel):
    id: str
    project_id: str
    title: str
    hook: str
    content: str
    language: str
    hashtags: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoiceGenerateRequest(BaseModel):
    project_id: str
    script_id: Optional[str] = None
    text: str
    voice_name: str = "arabic_default"


class AudioResponse(BaseModel):
    id: str
    project_id: str
    script_id: Optional[str]
    text: str
    voice_name: str
    audio_url: str
    credits_used: int
    duration_seconds: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VideoRenderRequest(BaseModel):
    project_id: str
    script_id: Optional[str] = None
    audio_id: Optional[str] = None
    title: str
    text: str
    audio_url: str

class VideoResponse(BaseModel):
    id: str
    project_id: str
    script_id: Optional[str]
    audio_id: Optional[str]
    title: str
    video_url: str
    credits_used: int
    duration_seconds: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
