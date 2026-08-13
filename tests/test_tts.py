import pytest
from fastapi.testclient import TestClient
from tts_service.main import app
from tts_service.fallback_tts import fallback_tts

client = TestClient(app)


def test_tts_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_tts_synthesize_endpoint():
    payload = {"text": "Aapka order confirm ho gaya hai", "language": "hi-IN", "use_cache": True}
    response = client.post("/synthesize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "audio_url" in data
    assert "audio_bytes_base64" in data
    assert data["characters_used"] > 0


@pytest.mark.asyncio
async def test_gtts_fallback_engine():
    bytes_data = await fallback_tts.synthesize_fallback("Aapka order confirm ho gaya hai", "hi-IN")
    assert bytes_data is not None
    assert len(bytes_data) > 0
