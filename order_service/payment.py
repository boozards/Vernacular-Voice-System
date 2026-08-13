import logging
from typing import Optional
from shared.config import settings

logger = logging.getLogger("order.payment")


class PaymentService:
    def generate_upi_link(self, order_id: str, amount: float, user_phone: str) -> str:
        """Generates UPI Payment Link via Razorpay API or UPI deeplink scheme."""
        if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_mock"):
            try:
                import razorpay
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                res = client.payment_link.create({
                    "amount": int(amount * 100),  # Amount in paise
                    "currency": "INR",
                    "accept_partial": False,
                    "reference_id": order_id,
                    "description": f"VoiceKart Order #{order_id[:8]}",
                    "customer": {"contact": user_phone},
                    "notify": {"sms": True, "email": False},
                    "reminder_enable": True,
                })
                return res.get("short_url", f"https://rzp.io/i/{order_id[:8]}")
            except Exception as e:
                logger.error(f"Razorpay link creation error: {e}")

        # Fallback UPI Deeplink format
        return f"upi://pay?pa=voicekart@razorpay&pn=VoiceKart&am={amount:.2f}&tr={order_id[:8]}&cu=INR"


payment_service = PaymentService()
