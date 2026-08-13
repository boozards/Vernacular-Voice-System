import logging
from fastapi import FastAPI, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config import settings
from shared.logging import setup_logger
from shared.middleware import CorrelationAndMetricsMiddleware
from shared.models import OrderCreateRequest, OrderResponse, CartItem
from order_service.db import init_db
from order_service.cart_manager import cart_manager
from order_service.order_manager import order_manager

setup_logger("order_service", settings.LOG_LEVEL)
logger = logging.getLogger("order_service")

app = FastAPI(
    title="VoiceKart Order Service",
    description="PostgreSQL-backed order, cart, payment integration, and status tracking service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationAndMetricsMiddleware, service_name="order_service")


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "order_service",
        "env": settings.ENV
    }


@app.post("/cart/add")
async def add_to_cart(payload: dict):
    session_id = payload.get("session_id", "default-session")
    item_data = payload.get("item", {})
    item = CartItem(**item_data)
    cart = await cart_manager.add_item(session_id, item)
    return {"status": "added", "cart": [c.model_dump() for c in cart]}


@app.get("/cart/{session_id}")
async def get_cart(session_id: str):
    cart = await cart_manager.get_cart(session_id)
    return {"cart": [c.model_dump() for c in cart]}


@app.post("/orders", response_model=OrderResponse)
async def create_order(req: OrderCreateRequest):
    try:
        order = await order_manager.create_order(req)
        return order
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation error: {str(e)}"
        )


@app.get("/orders/{user_phone}/latest", response_model=OrderResponse)
async def get_latest_order(user_phone: str):
    order = await order_manager.get_latest_user_order(user_phone)
    if not order:
        raise HTTPException(status_code=404, detail="No orders found for this user")
    return order


@app.post("/orders/{order_id}/status")
async def update_order_status(order_id: str, payload: dict):
    new_status = payload.get("status", "CONFIRMED")
    order = await order_manager.update_status(order_id, new_status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("order_service.main:app", host="0.0.0.0", port=8006, reload=True)
