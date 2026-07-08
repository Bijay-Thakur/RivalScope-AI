from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import config, evaluations, research, runs
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db

setup_logging()
init_db()
logger = get_logger(__name__)

app = FastAPI(
    title="RivalScope AI API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(runs.router)
app.include_router(evaluations.router)
app.include_router(config.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "rivalscope-api"}


if __name__ == "__main__":
    import uvicorn

    # Exclude runtime artifacts from --reload so log/DB writes during a long
    # research stream do not restart the server mid-request.
    reload_excludes = [
        "**/logs/**",
        "**/data/**",
        "**/eval_results/**",
        "**/__pycache__/**",
        "**/.pytest_cache/**",
    ]

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
        reload_excludes=reload_excludes,
    )
