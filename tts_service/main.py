import logging
from fastapi import FastAPI, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config import settings
from shared.logging import setup_logger
from shared.middleware import CorrelationAndMetricsMiddleware
from shared.models import TTSRequest, TTSResponse
from tts_service.elevenlabs_client import elevenlabs_client
from tts_service.cost_monitor import cost_monitor

setup_logger("tts_service", settings.LOG_LEVEL)
logger = logging.getLogger("tts_service")

app = FastAPI(
    title="VoiceKart TTS Service",
    description="ElevenLabs Text-to-Speech service with caching, fallback, and cost monitoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationAndMetricsMiddleware, service_name="tts_service")


@app.get("/health")
async def health_check():
    quota_pct = await cost_monitor.check_quota()
    return {
        "status": "healthy",
        "service": "tts_service",
        "elevenlabs_quota_remaining_pct": quota_pct,
        "env": settings.ENV
    }


@app.post("/synthesize", response_model=TTSResponse)
async def synthesize(req: TTSRequest):
    if not req.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text field cannot be empty"
        )

    try:
        url, b64, duration_ms, cached, chars = await elevenlabs_client.synthesize(
            text=req.text,
            language=req.language,
            use_cache=req.use_cache
        )
        return TTSResponse(
            audio_url=url,
            audio_bytes_base64=b64,
            duration_ms=duration_ms,
            cached=cached,
            characters_used=chars
        )
    except Exception as e:
        logger.error(f"Synthesis endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS error: {str(e)}"
        )


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tts_service.main:app", host="0.0.0.0", port=8003, reload=True)
