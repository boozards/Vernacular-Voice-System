from fastapi.testclient import TestClient
from catalog_service.main import app

client = TestClient(app)


def test_catalog_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_catalog_search():
    payload = {
        "query": "running shoes",
        "filters": {"price_max": 2500, "brands": ["Nike"]},
        "language": "hi-IN",
        "limit": 5
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert len(data["products"]) > 0
    assert data["products"][0]["brand"] == "Nike"
