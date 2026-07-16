from fastapi.testclient import TestClient

from app import data
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sectors():
    r = client.get("/sectors")
    assert r.status_code == 200
    sectors = r.json()
    assert len(sectors) == 9
    assert all({"id", "name_ar", "name_en"} <= s.keys() for s in sectors)


def test_sector_companies():
    r = client.get("/sectors/banks/companies")
    assert r.status_code == 200
    banks = r.json()
    assert len(banks) == 5
    assert any(c["is_islamic_bank"] for c in banks)


def test_sector_companies_404():
    assert client.get("/sectors/nope/companies").status_code == 404


def test_company_profile():
    r = client.get("/companies/1120")
    assert r.status_code == 200
    c = r.json()
    assert c["name_en"] == "Al Rajhi Bank"
    assert c["is_islamic_bank"] is True
    assert c["latest"]["quarter"] == "2026Q2"
    assert c["latest"]["revenue"] > 0


def test_company_404():
    assert client.get("/companies/0000").status_code == 404


def test_financials_history():
    r = client.get("/companies/2222/financials")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 12
    assert rows[0]["quarter"] == "2023Q3"
    assert rows[-1]["quarter"] == "2026Q2"
    assert all(row["zakat_expense"] >= 0 for row in rows)


def test_sukuk_flagged_separately():
    rows = client.get("/companies/1120/financials").json()
    assert all(0 < row["sukuk_debt"] <= row["total_debt"] for row in rows)
    rows = client.get("/companies/4190/financials").json()
    assert all(row["sukuk_debt"] == 0 for row in rows)


def test_news():
    r = client.get("/companies/7010/news")
    assert r.status_code == 200
    items = r.json()
    assert 4 <= len(items) <= 6
    assert all(item["headline"] and item["body"] for item in items)


def test_all_33_companies_have_profiles():
    sectors = client.get("/sectors").json()
    total = 0
    for s in sectors:
        companies = client.get(f"/sectors/{s['id']}/companies").json()
        total += len(companies)
        for c in companies:
            assert client.get(f"/companies/{c['ticker']}").status_code == 200
    assert total == 33


def test_subscribe_valid_invalid_and_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    monkeypatch.setattr(data, "SUBSCRIBERS_PATH", tmp_path / "subscribers.json")
    data.SUBSCRIBERS_PATH.write_text("[]", encoding="utf-8")

    payload = {
        "name": "Maha Alqahtani",
        "email": "maha@research.sa",
        "company": "Delta Capital",
    }
    first = client.post("/subscribe", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "created"
    assert len(data.subscribers()) == 1

    duplicate = client.post("/subscribe", json=payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"
    assert len(data.subscribers()) == 1

    invalid = client.post("/subscribe", json={**payload, "email": "not-an-email"})
    assert invalid.status_code == 422
