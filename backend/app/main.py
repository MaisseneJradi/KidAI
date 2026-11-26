from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, children
from app.core import metrics
from app.core.config import settings
from app.db import session

app = FastAPI(title="KidAI API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(metrics.track_requests)

app.include_router(auth.router)
app.include_router(children.router)
# Pour Prometheus, en local. À ne pas exposer publiquement en production.
app.add_api_route(metrics.METRICS_PATH, metrics.metrics, include_in_schema=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "database": "ok" if session.check_database() else "unavailable",
    }
