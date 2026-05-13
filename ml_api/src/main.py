import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from core.model_registry import registry
from schemas.request import AnalyzeChallengeRequest, AnalyzeMatchRequest
from schemas.response import ChallengeAnalysisResponse, MatchResponse
from services import verify_service

logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.load()
    yield


app = FastAPI(
    title="Face Verification ML API",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models": {
            "face_analyzer": registry._face_analyzer is not None
        }
    }


@app.post("/api/analyze/challenge", response_model=ChallengeAnalysisResponse)
async def analyze_challenge(request: AnalyzeChallengeRequest) -> ChallengeAnalysisResponse:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, verify_service.process_challenge, request
    )


@app.post("/api/analyze/match", response_model=MatchResponse)
async def analyze_match(request: AnalyzeMatchRequest) -> MatchResponse:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, verify_service.process_match, request
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})