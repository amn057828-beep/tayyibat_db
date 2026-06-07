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
from typing import Optional
from datetime import datetime

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

