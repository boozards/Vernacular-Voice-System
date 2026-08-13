import re
import httpx
import logging
from typing import Tuple, Optional
import base64

from shared.config import settings
from shared.s3_client import s3_storage
from tts_service.tts_cache import tts_cache
from tts_service.cost_monitor import cost_monitor
from tts_service.fallback_tts import fallback_tts

logger = logging.getLogger("tts.elevenlabs")

VOICE_MAP = {
    "hi-IN": {"voice_id": "21m00Tcm4TlvDq8ikWAM", "model": "eleven_multilingual_v2", "name": "Diya"},
    "ta-IN": {"voice_id": "AZnzlk1XvdvUeBnXmlld", "model": "eleven_multilingual_v2", "name": "Priya"},
    "te-IN": {"voice_id": "EXAVITQu4vr4xnSDxMaL", "model": "eleven_multilingual_v2", "name": "Lakshmi"},
    "bn-IN": {"voice_id": "ErXwobaYiN019PkySvjV", "model": "eleven_multilingual_v2", "name": "Ananya"},
    "mr-IN": {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "model": "eleven_multilingual_v2", "name": "Sneha"},
    "kn-IN": {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "model": "eleven_multilingual_v2", "name": "Kavya"},
    "ml-IN": {"voice_id": "VR6AewLTigWG4xSOukaG", "model": "eleven_multilingual_v2", "name": "Meera"},
    "gu-IN": {"voice_id": "pNInz6obpgDQGcFmaJgB", "model": "eleven_multilingual_v2", "name": "Riya"},
    "en-IN": {"voice_id": "21m00Tcm4TlvDq8ikWAM", "model": "eleven_multilingual_v2", "name": "Diya"}
}

VOICE_SETTINGS = {
    "stability": 0.6,
    "similarity_boost": 0.78,
    "style": 0.35,
    "use_speaker_boost": True
}


def preprocess_ssml(text: str) -> str:
    """Preprocesses text to insert natural speech pauses before prices and numbers."""
    # Add slight pause before price patterns (e.g. ₹1,899 -> sirf... ₹1,899)
    text = re.sub(r'₹(\d+)', r'sirf... ₹\1', text)
    return text


class ElevenLabsClient:
    async def synthesize(
        self, text: str, language: str = "hi-IN", use_cache: bool = True
    ) -> Tuple[str, str, float, bool, int]:
        """
        Synthesizes text to audio.
        Returns: (audio_url, base64_audio, duration_ms, cached, characters_used)
        """
        clean_text = preprocess_ssml(text)
        char_count = len(clean_text)

        voice_config = VOICE_MAP.get(language, VOICE_MAP["hi-IN"])
        voice_id = voice_config["voice_id"]
        model_id = voice_config["model"]

        # 1. Check Redis Cache
        if use_cache:
            cached_bytes = await tts_cache.get(clean_text, voice_id, VOICE_SETTINGS)
            if cached_bytes:
                key, url = await s3_storage.upload_audio_bytes(cached_bytes, extension="mp3")
                b64 = base64.b64encode(cached_bytes).decode("utf-8")
                return url, b64, 2500.0, True, char_count

        # 2. Try ElevenLabs API if API key valid
        if not settings.ELEVENLABS_API_KEY.startswith("mock"):
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            headers = {
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": clean_text,
                "model_id": model_id,
                "voice_settings": VOICE_SETTINGS
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        audio_bytes = resp.content
                        cost_monitor.record_usage(char_count, language)

                        # Store in Cache
                        await tts_cache.set(clean_text, voice_id, VOICE_SETTINGS, audio_bytes)

                        # Upload to S3
                        key, s3_url = await s3_storage.upload_audio_bytes(audio_bytes, extension="mp3")
                        b64 = base64.b64encode(audio_bytes).decode("utf-8")
                        return s3_url, b64, 3200.0, False, char_count
                    elif resp.status_code == 429:
                        logger.warning("ElevenLabs Rate Limited (429)! Triggering fallback.")
                        cost_monitor.record_fallback("rate_limit_429")
                    else:
                        logger.error(f"ElevenLabs API error {resp.status_code}: {resp.text}")
                        cost_monitor.record_fallback(f"error_{resp.status_code}")
                except Exception as e:
                    logger.error(f"Failed ElevenLabs API request: {e}")
                    cost_monitor.record_fallback("connection_exception")

        # 3. Fallback TTSEngine (gTTS)
        logger.info("Executing Fallback TTS Engine")
        fallback_bytes = await fallback_tts.synthesize_fallback(clean_text, language)
        key, s3_url = await s3_storage.upload_audio_bytes(fallback_bytes, extension="mp3")
        b64 = base64.b64encode(fallback_bytes).decode("utf-8")
        return s3_url, b64, 2000.0, False, char_count


elevenlabs_client = ElevenLabsClient()
