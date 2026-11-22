from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, children, parent
from app.core.config import settings
from app.db import session

app = FastAPI(title="KidAI API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(children.router)
app.include_router(chat.router)
app.include_router(parent.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "database": "ok" if session.check_database() else "unavailable",
    }
