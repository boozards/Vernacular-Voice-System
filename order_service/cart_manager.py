import logging
from typing import List, Dict
from shared.models import CartItem

logger = logging.getLogger("order.cart")

# In-memory storage fallback for cart
IN_MEMORY_CARTS: Dict[str, List[CartItem]] = {}


class CartManager:
    async def add_item(self, session_id: str, item: CartItem) -> List[CartItem]:
        if session_id not in IN_MEMORY_CARTS:
            IN_MEMORY_CARTS[session_id] = []

        # Check if product already in cart
        existing = next((i for i in IN_MEMORY_CARTS[session_id] if i.product_id == item.product_id), None)
        if existing:
            existing.quantity += item.quantity
        else:
            IN_MEMORY_CARTS[session_id].append(item)

        return IN_MEMORY_CARTS[session_id]

    async def get_cart(self, session_id: str) -> List[CartItem]:
        return IN_MEMORY_CARTS.get(session_id, [])

    async def clear_cart(self, session_id: str) -> None:
        if session_id in IN_MEMORY_CARTS:
            IN_MEMORY_CARTS[session_id].clear()


cart_manager = CartManager()
