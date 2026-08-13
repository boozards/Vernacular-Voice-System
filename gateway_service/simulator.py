import time
import base64
import httpx
import logging
from fastapi import APIRouter, HTTPException, status
from shared.config import settings
from shared.models import SimulateRequest, SimulateResponse
from shared.s3_client import s3_storage

logger = logging.getLogger("gateway.simulator")
router = APIRouter()


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_voice_commerce(req: SimulateRequest):
    """
    Testing endpoint allowing developers/testers to trigger full end-to-end voice commerce flow 
    without needing a WhatsApp Business API account.
    Accepts text input OR base64-encoded audio, returns transcribed text, intent, text response, 
    and synthesized audio.
    """
    start_time = time.time()
    audio_s3_key = None

    if req.audio_bytes_base64:
        try:
            audio_bytes = base64.b64decode(req.audio_bytes_base64)
            audio_s3_key, _ = await s3_storage.upload_audio_bytes(audio_bytes, extension="ogg")
        except Exception as e:
            logger.error(f"Failed to process base64 audio in simulator: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 audio content: {str(e)}"
            )

    if not req.text_input and not audio_s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text_input or audio_bytes_base64 must be provided."
        )

    orchestrator_payload = {
        "user_phone": req.user_phone,
        "audio_s3_key": audio_s3_key,
        "text_input": req.text_input,
        "forced_language": req.language
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/orchestrate",
                json=orchestrator_payload
            )

            if resp.status_code != 200:
                logger.error(f"Orchestrator error status {resp.status_code}: {resp.text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Orchestrator error: {resp.text}"
                )

            res_data = resp.json()
            latency_ms = round((time.time() - start_time) * 1000, 2)

            audio_url = res_data.get("audio_url", "")
            audio_bytes_base64 = res_data.get("audio_bytes_base64")

            # If audio_url exists but base64 not populated, download bytes to encode base64
            if not audio_bytes_base64 and audio_url:
                try:
                    s3_key = res_data.get("audio_s3_key") or audio_url
                    b_data = await s3_storage.download_audio_bytes(s3_key)
                    if b_data:
                        audio_bytes_base64 = base64.b64encode(b_data).decode("utf-8")
                except Exception as e:
                    logger.warning(f"Could not encode audio to base64: {e}")

            return SimulateResponse(
                session_id=res_data.get("session_id", "sim-session"),
                transcribed_text=res_data.get("transcribed_text", req.text_input or ""),
                detected_language=res_data.get("detected_language", req.language or "hi-IN"),
                extracted_intent=res_data.get("extracted_intent", "UNKNOWN"),
                response_text=res_data.get("response_text", ""),
                audio_url=audio_url,
                audio_bytes_base64=audio_bytes_base64,
                latency_ms=latency_ms,
                cart=res_data.get("cart", []),
                search_results_count=res_data.get("search_results_count", 0)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simulation failed with unhandled exception: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulator internal error: {str(e)}"
        )
