from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from src.helpers.config import settings
from src.routes.say_writer import essay_router, say_writer
from src.schemas.say_writer import EssayRequest, EssayResponse

# Resolve frontend file paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

INDEX_FILE = SRC_DIR / "views" / "index.html"
if not INDEX_FILE.exists():
    INDEX_FILE = PROJECT_ROOT / "Views" / "index.html"

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Agentic Essay Writer Service with automated research and reflective revisions",
)

# Register route prefixed with /api/v1/essay
app.include_router(essay_router)


# Root alias for /say_writer
@app.post("/say_writer", response_model=EssayResponse, tags=["Essay Writer"], include_in_schema=False)
async def root_say_writer(payload: EssayRequest):
    return await say_writer(payload)


@app.get("/", response_class=FileResponse, tags=["Frontend"])
async def root():
    """Serves the frontend view (index.html)."""
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return {"status": "healthy", "app_name": settings.APP_NAME}


@app.get("/health", tags=["Health"])
async def health():
    """Health check and service status."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "model": settings.MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
