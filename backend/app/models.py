import uuid

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="USER")
    credits = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    scripts = relationship("Script", back_populates="user", cascade="all, delete-orphan")
    audios = relationship("Audio", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    type = Column(String, default="SCRIPT")
    status = Column(String, default="DRAFT")
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="projects")
    scripts = relationship("Script", back_populates="project", cascade="all, delete-orphan")
    audios = relationship("Audio", back_populates="project", cascade="all, delete-orphan")


class Script(Base):
    __tablename__ = "scripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    hook = Column(String, nullable=False)
    content = Column(String, nullable=False)
    language = Column(String, default="ar")
    hashtags = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="scripts")
    user = relationship("User", back_populates="scripts")
    audios = relationship("Audio", back_populates="script")


class Audio(Base):
    __tablename__ = "audios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    script_id = Column(String, ForeignKey("scripts.id"), nullable=True, index=True)
    text = Column(String, nullable=False)
    voice_name = Column(String, default="arabic_default")
    audio_url = Column(String, nullable=False)
    credits_used = Column(Integer, default=1)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="audios")
    user = relationship("User", back_populates="audios")
    script = relationship("Script", back_populates="audios")

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    script_id = Column(String, ForeignKey("scripts.id"), nullable=True, index=True)
    audio_id = Column(String, ForeignKey("audios.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    credits_used = Column(Integer, default=2)
    duration_seconds = Column(Integer, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    script_id = Column(String, ForeignKey("scripts.id"), nullable=False, index=True)
    scene_number = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    image_prompt = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    duration_seconds = Column(Integer, default=6)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
