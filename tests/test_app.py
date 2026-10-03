from fastapi.testclient import TestClient

from superai_review.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_exposes_brand_not_internal_config() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "SuperAI.review"
    assert "database_url" not in body
