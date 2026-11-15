"""API tests for server.py using FastAPI's TestClient (no network, no LLM)."""

import os
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import server  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    # Make sure no Azure OpenAI backend is used, so tests stay offline.
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    # Entering the context manager runs the app lifespan, which creates the agent.
    with TestClient(server.app) as c:
        yield c


def test_health_reports_tools(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert len(body["available_tools"]) > 0


def test_tools_lists_definitions(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    assert len(resp.json()["tools"]) > 0


def test_calendars(client):
    resp = client.get("/calendars")
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()["calendars"]}
    assert ids == {"GREGORIAN", "PERU_BANKING"}


def test_examples(client):
    resp = client.get("/examples")
    assert resp.status_code == 200
    assert resp.json()["examples"]


def test_holidays_peru_july(client):
    resp = client.post(
        "/holidays",
        json={"calendar_system": "PERU_BANKING", "year": 2024, "month": 7},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == len(body["holidays"])
    assert body["count"] >= 1
    assert all(h["date"].startswith("2024-07") for h in body["holidays"])


def test_holidays_unknown_calendar_is_400(client):
    resp = client.post("/holidays", json={"calendar_system": "NOPE", "year": 2024})
    assert resp.status_code == 400


def test_query_returns_structured_result(client):
    resp = client.post("/query", json={"query": "julio 2024"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "julio 2024"
    assert "success" in body


def test_query_requires_query_field(client):
    resp = client.post("/query", json={})
    assert resp.status_code == 422


def test_health_503_without_agent(monkeypatch):
    # Without entering the lifespan, the global agent is not initialised.
    monkeypatch.setattr(server, "agent", None)
    resp = TestClient(server.app).get("/health")
    assert resp.status_code == 503
