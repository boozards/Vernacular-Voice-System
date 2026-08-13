from fastapi.testclient import TestClient
from gateway_service.main import app
from shared.config import settings

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway_service"


def test_webhook_verification_success():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "12345678"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "12345678"


def test_webhook_verification_failure():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "12345678"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403


from unittest.mock import patch, MagicMock

def test_simulator_text_query():
    payload = {
        "user_phone": "+919876543210",
        "text_input": "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9",
        "language": "hi-IN"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "session_id": "sess_sim_123",
        "transcribed_text": "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9",
        "detected_language": "hi-IN",
        "extracted_intent": "PRODUCT_SEARCH",
        "response_text": "Ji bilkul! Maine 3 options dhundhe hain.",
        "audio_url": "http://localhost:9000/audio/123.mp3",
        "cart": [],
        "search_results_count": 2
    }

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        response = client.post("/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "transcribed_text" in data
        assert data["detected_language"] == "hi-IN"
        assert data["extracted_intent"] == "PRODUCT_SEARCH"
        assert "response_text" in data
        assert data["latency_ms"] >= 0

