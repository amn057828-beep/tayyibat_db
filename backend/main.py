from fastapi import FastAPI
from app.database import Base, engine
from app.auth import router as auth_router
from app.projects import router as projects_router
from app.ai import router as ai_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CreatorFlow AI API",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(ai_router)

@app.get("/")
def root():
    return {
        "status": "running",
        "app": "CreatorFlow AI"
    }

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
