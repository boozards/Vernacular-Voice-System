import httpx
import logging
from prometheus_client import Counter, Gauge

from shared.config import settings

logger = logging.getLogger("tts.cost_monitor")

CHARACTERS_USED = Counter(
    "voicekart_elevenlabs_characters_used",
    "Total characters synthesized using ElevenLabs",
    ["language"]
)

QUOTA_REMAINING_PCT = Gauge(
    "voicekart_elevenlabs_quota_remaining_pct",
    "Percentage of monthly ElevenLabs quota remaining"
)

FALLBACK_TTS_ACTIVATIONS = Counter(
    "voicekart_fallback_tts_activations_total",
    "Total times fallback TTS was activated",
    ["reason"]
)


class CostMonitor:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"

    def record_usage(self, character_count: int, language: str):
        CHARACTERS_USED.labels(language=language).inc(character_count)

    def record_fallback(self, reason: str):
        FALLBACK_TTS_ACTIVATIONS.labels(reason=reason).inc()

    async def check_quota(self) -> float:
        """Fetches quota remaining percentage from ElevenLabs API."""
        if settings.ELEVENLABS_API_KEY.startswith("mock"):
            QUOTA_REMAINING_PCT.set(100.0)
            return 100.0

        headers = {"xi-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/user/subscription", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    used = data.get("character_count", 0)
                    limit = data.get("character_limit", 10000)
                    remaining_pct = max(0.0, ((limit - used) / max(1, limit)) * 100)
                    QUOTA_REMAINING_PCT.set(remaining_pct)
                    if remaining_pct < settings.ELEVENLABS_QUOTA_ALERT_THRESHOLD_PCT:
                        logger.warning(f"ALERT: ElevenLabs quota low! Remaining: {remaining_pct:.1f}%")
                    return remaining_pct
            except Exception as e:
                logger.error(f"Failed checking ElevenLabs subscription quota: {e}")
        return 100.0


cost_monitor = CostMonitor()
