from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.auth import router as auth_router
from app.projects import router as projects_router
from app.ai import router as ai_router
from app.users import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CreatorFlow AI API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(ai_router)
app.include_router(users_router)

@app.get("/")
def root():
    return {"status": "running", "app": "CreatorFlow AI"}

@app.get("/health")
def health():
    return {"status": "ok"}
