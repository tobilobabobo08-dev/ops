"""Tests for contacts collection and request-response logging endpoints."""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import requires_db


@pytest.mark.asyncio
@requires_db
async def test_create_and_list_contact(client: httpx.AsyncClient) -> None:
    """Test POST /api/v1/contacts creates an entry and GET returns it."""
    payload = {"name": "Alice Smith", "phone_number": "+1234567890"}
    response = await client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Smith"
    assert data["phone_number"] == "+1234567890"
    assert "id" in data
    assert "created_at" in data

    list_resp = await client.get("/api/v1/contacts")
    assert list_resp.status_code == 200
    page_data = list_resp.json()
    assert page_data["total"] >= 1
    assert any(item["name"] == "Alice Smith" for item in page_data["items"])


@pytest.mark.asyncio
@requires_db
async def test_create_and_list_request_response_logs(client: httpx.AsyncClient) -> None:
    """Test POST /api/v1/request-responses saves log and GET retrieves logged requests."""
    # First make a request to trigger middleware logging
    await client.post(
        "/api/v1/contacts",
        json={"name": "Bob Marley", "phone_number": "+9876543210"},
    )

    list_resp = await client.get("/api/v1/request-responses")
    assert list_resp.status_code == 200
    page_data = list_resp.json()
    assert page_data["total"] >= 1
    # Check that the request to /api/v1/contacts was logged automatically by middleware
    paths = [item["path"] for item in page_data["items"]]
    assert "/api/v1/contacts" in paths
