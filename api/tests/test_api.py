"""Tests for the FastAPI REST API endpoints."""

from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.api.app import app
from app.models.api import JobResult, JobStatus

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestResearchEndpoints:
    @patch("app.api.routes.create_job")
    def test_submit_research_returns_202(self, mock_create):
        mock_create.return_value = JobResult(
            job_id="test123",
            status=JobStatus.PENDING,
            question="What is ML?",
        )
        resp = client.post("/api/research", json={"question": "What is ML?"})
        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == "test123"
        assert data["status"] == "pending"

    def test_submit_empty_question_returns_400(self):
        resp = client.post("/api/research", json={"question": "   "})
        assert resp.status_code == 400

    @patch("app.api.routes.get_job")
    def test_get_research_returns_job(self, mock_get):
        mock_get.return_value = JobResult(
            job_id="test123",
            status=JobStatus.COMPLETED,
            question="Q",
            report="# Done",
        )
        resp = client.get("/api/research/test123")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    @patch("app.api.routes.get_job")
    def test_get_unknown_job_returns_404(self, mock_get):
        mock_get.return_value = None
        resp = client.get("/api/research/nonexistent")
        assert resp.status_code == 404

    @patch("app.api.routes.list_jobs")
    def test_list_research_returns_list(self, mock_list):
        mock_list.return_value = []
        resp = client.get("/api/research")
        assert resp.status_code == 200
        assert resp.json() == []


class TestWebhookEndpoints:
    @patch("app.api.webhook.config")
    def test_whatsapp_verify_success(self, mock_config):
        mock_config.WHATSAPP_VERIFY_TOKEN = "test-token"
        resp = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == 12345

    @patch("app.api.webhook.config")
    def test_whatsapp_verify_fails_bad_token(self, mock_config):
        mock_config.WHATSAPP_VERIFY_TOKEN = "correct"
        resp = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 403

    @patch("app.api.webhook.create_job")
    def test_generic_webhook_creates_job(self, mock_create):
        mock_create.return_value = JobResult(
            job_id="wh001",
            status=JobStatus.PENDING,
            question="Webhook Q",
        )
        resp = client.post(
            "/webhook/inbound",
            json={"message": "Webhook Q", "source": "slack"},
        )
        assert resp.status_code == 200
        assert resp.json()["job_id"] == "wh001"

    def test_generic_webhook_rejects_empty_message(self):
        resp = client.post(
            "/webhook/inbound",
            json={"message": "   "},
        )
        assert resp.status_code == 400
