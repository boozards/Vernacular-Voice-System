from fastapi.testclient import TestClient
from stt_service.main import app

client = TestClient(app)


def test_stt_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_stt_transcribe_fallback():
    payload = {"expected_language": "hi-IN"}
    response = client.post("/transcribe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert data["detected_language"] == "hi-IN"
    assert data["confidence"] > 0.5
