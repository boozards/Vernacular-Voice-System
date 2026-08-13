from fastapi.testclient import TestClient
from order_service.main import app

client = TestClient(app)


def test_order_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_cart_operations():
    payload = {
        "session_id": "test-sess-100",
        "item": {
            "product_id": "SKU-RUN-NK-001",
            "title": "Nike Revolution 6",
            "quantity": 1,
            "price": 1899.0
        }
    }
    resp = client.post("/cart/add", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cart"]) == 1


def test_order_creation():
    payload = {
        "user_phone": "+919876543210",
        "cart_items": [
            {
                "product_id": "SKU-RUN-NK-001",
                "title": "Nike Revolution 6",
                "quantity": 1,
                "price": 1899.0
            }
        ],
        "payment_method": "COD"
    }
    resp = client.post("/orders", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["payment_method"] == "COD"
    assert data["status"] == "CONFIRMED"
