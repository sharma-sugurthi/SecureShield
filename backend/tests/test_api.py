"""
Tests for the API endpoints.
Uses FastAPI TestClient for synchronous testing.
No LLM calls required — tests use mock data and direct endpoint testing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app
from security import get_or_create_master_key


@pytest.fixture(scope="module")
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def api_key():
    """Get a valid API key."""
    return get_or_create_master_key()


# ============================================================
# Health Check
# ============================================================

class TestHealthCheck:

    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "SecureShield"

    def test_health_no_auth_required(self, client):
        """Health check should work without API key."""
        response = client.get("/api/health")
        assert response.status_code == 200


# ============================================================
# Authentication Tests
# ============================================================

class TestAuthentication:

    def test_list_policies_requires_auth(self, client):
        """Endpoints should reject requests without API key."""
        response = client.get("/api/policies")
        assert response.status_code == 401

    def test_list_policies_rejects_invalid_key(self, client):
        """Invalid API key should be rejected."""
        response = client.get(
            "/api/policies",
            headers={"X-API-Key": "invalid_key_123"}
        )
        assert response.status_code == 403

    def test_list_policies_accepts_valid_key(self, client, api_key):
        """Valid API key should work."""
        response = client.get(
            "/api/policies",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200

    def test_upload_requires_auth(self, client):
        response = client.post("/api/upload-policy")
        assert response.status_code == 401

    def test_check_eligibility_requires_auth(self, client):
        response = client.post("/api/check-eligibility", json={})
        assert response.status_code == 401

    def test_history_requires_auth(self, client):
        response = client.get("/api/history")
        assert response.status_code == 401


# ============================================================
# Input Validation Tests
# ============================================================

class TestInputValidation:

    def test_upload_rejects_non_pdf(self, client, api_key):
        """Non-PDF files should be rejected."""
        response = client.post(
            "/api/upload-policy",
            headers={"X-API-Key": api_key},
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_eligibility_rejects_invalid_body(self, client, api_key):
        """Invalid request body should return 422."""
        response = client.post(
            "/api/check-eligibility",
            headers={"X-API-Key": api_key},
            json={"invalid": "data"},
        )
        assert response.status_code == 422

    def test_history_rejects_invalid_limit(self, client, api_key):
        """Limit out of range should be rejected."""
        response = client.get(
            "/api/history?limit=999",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 400

    def test_policy_not_found(self, client, api_key):
        """Non-existent policy should return 404."""
        response = client.get(
            "/api/policies/99999",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 404


# ============================================================
# Policy Listing
# ============================================================

class TestPolicyListing:

    def test_empty_policies_list(self, client, api_key):
        """Should return empty list when no policies uploaded."""
        response = client.get(
            "/api/policies",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert isinstance(data["policies"], list)
        assert "count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
