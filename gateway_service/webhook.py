import httpx
import logging
import secrets
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, Query, HTTPException, status
from shared.config import settings
from shared.s3_client import s3_storage
from gateway_service.whatsapp_client import whatsapp_client

logger = logging.getLogger("gateway.webhook")
router = APIRouter()


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge"),
):
    """WhatsApp Cloud API Webhook Verification Challenge."""
    if mode == "subscribe" and secrets.compare_digest(token, settings.WHATSAPP_VERIFY_TOKEN):
        logger.info("WhatsApp webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"Webhook verification failed. Token mismatch: {token}")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@router.post("/webhook")
async def handle_incoming_webhook(request: Request):
    """Handles incoming WhatsApp Cloud API messages (text, audio, buttons)."""
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Verify signature in production
    if settings.ENV == "production" and not whatsapp_client.verify_signature(raw_body, signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        body = await request.json()
    except Exception:
        logger.warning("Received malformed JSON payload in webhook")
        return {"status": "ignored"}

    # Extract entry data
    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                await process_message(msg, value)

    return {"status": "ok"}


async def process_message(msg: Dict[str, Any], value: Dict[str, Any]):
    msg_id = msg.get("id")
    from_phone = msg.get("from")
    msg_type = msg.get("type")

    if not msg_id or not from_phone:
        return

    # Check deduplication
    if await whatsapp_client.is_duplicate_message(msg_id):
        logger.info(f"Duplicate message received: {msg_id}, ignoring")
        return

    audio_s3_key = None
    text_input = None

    if msg_type == "audio":
        audio_info = msg.get("audio", {})
        media_id = audio_info.get("id")
        if media_id:
            audio_bytes = await whatsapp_client.download_media(media_id)
            if not audio_bytes:
                await whatsapp_client.send_text(
                    from_phone,
                    "Mujhe aapka aawaz saaf nahi sunai diya. Kya aap dubara bol sakte hain?"
                )
                return
            
            # Upload to S3/MinIO
            audio_s3_key, _ = await s3_storage.upload_audio_bytes(audio_bytes, extension="ogg")

    elif msg_type == "text":
        text_input = msg.get("text", {}).get("body")

    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        if interactive.get("type") == "button_reply":
            text_input = interactive.get("button_reply", {}).get("title")

    else:
        logger.info(f"Unsupported message type: {msg_type}")
        return

    # Dispatch to Conversation Orchestrator Service
    orchestrator_payload = {
        "user_phone": from_phone,
        "audio_s3_key": audio_s3_key,
        "text_input": text_input,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/orchestrate",
                json=orchestrator_payload
            )
            if resp.status_code == 200:
                result = resp.json()
                audio_url = result.get("audio_url")
                response_text = result.get("response_text")

                # Send outbound voice message or text fallback
                if audio_url:
                    await whatsapp_client.send_voice(from_phone, audio_url)
                elif response_text:
                    await whatsapp_client.send_text(from_phone, response_text)
            else:
                logger.error(f"Orchestrator error status {resp.status_code}: {resp.text}")
                await whatsapp_client.send_text(
                    from_phone,
                    "Khabar Mili Hai Ki System mein thodi samasya hai. Kripya thodi der baad prayas karein."
                )

    except Exception as e:
        logger.error(f"Error forwarding message to Orchestrator: {e}")
        await whatsapp_client.send_text(
            from_phone,
            "Khabar Mili Hai Ki System mein thodi samasya hai. Kripya thodi der baad prayas karein."
        )
