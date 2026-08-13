import uuid
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

from shared.config import settings
from shared.models import OrderResponse, OrderCreateRequest, CartItem
from order_service.payment import payment_service

logger = logging.getLogger("order.manager")

# In-memory storage fallback for orders
IN_MEMORY_ORDERS: Dict[str, Dict[str, Any]] = {}


class OrderManager:
    async def create_order(self, req: OrderCreateRequest) -> OrderResponse:
        order_id = str(uuid.uuid4())
        
        subtotal = sum(item.price * item.quantity for item in req.cart_items)
        if subtotal == 0:
            subtotal = 1899.0  # Fallback default price

        gst = round(subtotal * 0.18, 2)
        delivery_fee = 0.0 if subtotal >= 999.0 else 49.0
        total = round(subtotal + gst + delivery_fee, 2)

        payment_link = None
        if req.payment_method == "UPI":
            payment_link = payment_service.generate_upi_link(order_id, total, req.user_phone)

        order_data = {
            "id": order_id,
            "user_phone": req.user_phone,
            "items": [item.model_dump() for item in req.cart_items],
            "subtotal": subtotal,
            "gst": gst,
            "delivery_fee": delivery_fee,
            "total": total,
            "payment_method": req.payment_method,
            "payment_status": "PAID" if req.payment_method == "COD" else "PENDING",
            "delivery_address": req.delivery_address or {"address": "Indore, MP", "pincode": "452001"},
            "status": "CONFIRMED",
            "payment_link": payment_link,
            "created_at": datetime.now(UTC).isoformat()
        }

        IN_MEMORY_ORDERS[order_id] = order_data
        logger.info(f"Order created successfully: {order_id} for user {req.user_phone}")

        return OrderResponse(**order_data)

    async def update_status(self, order_id: str, new_status: str) -> Optional[OrderResponse]:
        """Updates order status and triggers proactive voice update to user."""
        order_data = IN_MEMORY_ORDERS.get(order_id)
        if not order_data:
            return None

        old_status = order_data["status"]
        order_data["status"] = new_status
        logger.info(f"Order {order_id} status changed: {old_status} -> {new_status}")

        # Proactive voice update to user
        await self._trigger_proactive_voice_notification(order_data)

        return OrderResponse(**order_data)

    async def _trigger_proactive_voice_notification(self, order_data: Dict[str, Any]):
        """Triggers a TTS voice message to user on status change."""
        user_phone = order_data["user_phone"]
        status = order_data["status"]

        msg = f"Aapke order ID {order_data['id'][:8]} ka status abhi '{status}' ho gaya hai. Agle update ki jankari jald hi di jayegi."
        if status == "SHIPPED":
            msg = f"Aapka order ID {order_data['id'][:8]} ship ho gaya hai. Delivery kal tak ho jayegi."
        elif status == "OUT_FOR_DELIVERY":
            msg = f"Aapka order ID {order_data['id'][:8]} out for delivery hai. Aaj hi delivery agent aapko sampark karega."

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{settings.GATEWAY_SERVICE_URL}/webhook",
                    json={"event": "proactive_notification", "phone": user_phone, "text": msg}
                )
        except Exception as e:
            logger.warning(f"Could not dispatch proactive notification: {e}")

    async def get_latest_user_order(self, user_phone: str) -> Optional[OrderResponse]:
        user_orders = [o for o in IN_MEMORY_ORDERS.values() if o["user_phone"] == user_phone]
        if not user_orders:
            return None
        latest = sorted(user_orders, key=lambda x: x["created_at"], reverse=True)[0]
        return OrderResponse(**latest)


order_manager = OrderManager()
