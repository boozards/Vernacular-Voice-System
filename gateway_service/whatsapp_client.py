import hmac
import hashlib
import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
import redis.asyncio as redis

from shared.config import settings

logger = logging.getLogger("gateway.whatsapp")

# Setup Redis connection for deduplication
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)


class WhatsAppClient:
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.app_secret = settings.WHATSAPP_APP_SECRET
        self.base_url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"

    def verify_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """Verifies WhatsApp Cloud API X-Hub-Signature-256 header."""
        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header")
            return False

        if not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header.split("sha256=")[1]
        computed_sig = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_sig, computed_sig)

    async def is_duplicate_message(self, message_id: str) -> bool:
        """Deduplicates incoming webhook events using Redis SET NX (1 hour TTL)."""
        try:
            is_new = await redis_client.set(f"wa_msg:{message_id}", "1", nx=True, ex=3600)
            return not is_new
        except Exception as e:
            logger.error(f"Redis deduplication error: {e}")
            return False

    async def download_media(self, media_id: str) -> Optional[bytes]:
        """Downloads voice note media from WhatsApp CDN with 3 retries."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Fetch Media URL
            media_info_url = f"{self.base_url}/{media_id}"
            for attempt in range(1, 4):
                try:
                    resp = await client.get(media_info_url, headers=headers)
                    if resp.status_code == 200:
                        media_url = resp.json().get("url")
                        if media_url:
                            # Step 2: Download Media Content
                            download_resp = await client.get(media_url, headers=headers)
                            if download_resp.status_code == 200:
                                return download_resp.content
                    logger.warning(f"Media download attempt {attempt} failed with status {resp.status_code}")
                except Exception as e:
                    logger.error(f"Media download error attempt {attempt}: {e}")
                
                await asyncio.sleep(0.5 * (2 ** attempt))

        return None

    async def send_text(self, to_phone: str, text: str) -> bool:
        """Sends an outbound text message to user via WhatsApp Cloud API."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"body": text},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                return resp.status_code in (200, 201)
            except Exception as e:
                logger.error(f"Failed to send text message to {to_phone}: {e}")
                return False

    async def send_voice(self, to_phone: str, audio_url: str) -> bool:
        """Sends an outbound voice note to user via WhatsApp Cloud API."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "audio",
            "audio": {"link": audio_url},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                return resp.status_code in (200, 201)
            except Exception as e:
                logger.error(f"Failed to send voice message to {to_phone}: {e}")
                return False

    async def send_interactive_buttons(
        self, to_phone: str, body_text: str, buttons: list
    ) -> bool:
        """Sends interactive product cards/buttons to user."""
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                return resp.status_code in (200, 201)
            except Exception as e:
                logger.error(f"Failed to send interactive message to {to_phone}: {e}")
                return False


whatsapp_client = WhatsAppClient()
