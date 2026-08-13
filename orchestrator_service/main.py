import logging
from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config import settings
from shared.logging import setup_logger
from shared.middleware import CorrelationAndMetricsMiddleware
from orchestrator_service.orchestrator import pipeline_orchestrator

setup_logger("orchestrator_service", settings.LOG_LEVEL)
logger = logging.getLogger("orchestrator_service")

app = FastAPI(
    title="VoiceKart Conversation Orchestrator Service",
    description="Core Brain managing state transitions, LLM intents, session state, and service orchestration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationAndMetricsMiddleware, service_name="orchestrator_service")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "orchestrator_service",
        "env": settings.ENV
    }


@app.post("/orchestrate")
async def orchestrate(request: Request):
    payload = await request.json()
    result = await pipeline_orchestrator.process_user_turn(payload)
    return result


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator_service.main:app", host="0.0.0.0", port=8002, reload=True)
