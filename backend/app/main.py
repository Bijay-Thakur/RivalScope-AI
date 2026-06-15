from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import research
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

setup_logging()
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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "rivalscope-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
