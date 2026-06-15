from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rivalscope-api"


def test_create_research_returns_report():
    payload = {
        "ourCompany": "ClickUp",
        "competitor": "Notion",
        "market": "Project management / docs",
        "reportType": "sales_battlecard",
    }
    response = client.post("/api/research/", json=payload)
    assert response.status_code == 200

    report = response.json()["report"]
    assert "companySnapshot" in report
    assert report["companySnapshot"]
    assert "salesBattlecard" in report
    assert report["salesBattlecard"]
    assert "sources" in report
    assert len(report["sources"]) > 0
