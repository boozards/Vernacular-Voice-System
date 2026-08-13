import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config import settings
from shared.logging import setup_logger
from shared.middleware import CorrelationAndMetricsMiddleware
from gateway_service.webhook import router as webhook_router
from gateway_service.simulator import router as simulator_router

setup_logger("gateway_service", settings.LOG_LEVEL)
logger = logging.getLogger("gateway_service")

app = FastAPI(
    title="VoiceKart Gateway Service",
    description="WhatsApp Webhook & Simulation Gateway Service for VoiceKart",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationAndMetricsMiddleware, service_name="gateway_service")

app.include_router(webhook_router)
app.include_router(simulator_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gateway_service",
        "env": settings.ENV
    }


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway_service.main:app", host="0.0.0.0", port=8001, reload=True)
