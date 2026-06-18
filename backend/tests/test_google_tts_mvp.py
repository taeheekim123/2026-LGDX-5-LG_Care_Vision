from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def test_ar_guide_steps_include_tts_metadata(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_enabled"] is True
    assert first_step["tts_text"] == first_step["display_instruction"]
    assert first_step["tts_language_code"] == "en-IN"
    assert first_step["tts_provider"] in {"web_speech", "google_cloud_tts"}
    assert first_step["audio_url"] is None


def test_google_tts_provider_is_selected_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_TTS_ENABLED", "1")
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/ar/plans",
            json={
                "user_id": "U001",
                "device_id": "D001",
                "message": "Please help me clean the AC filter.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    first_step = response.json()["ar_overlay_data"]["guide_steps"][0]
    assert first_step["tts_provider"] == "google_cloud_tts"


def test_google_tts_endpoint_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_TTS_ENABLED", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/v1/tts/synthesize",
        json={
            "text": "Turn off the air conditioner before opening the front cover.",
            "language_code": "en-IN",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Google TTS is disabled"
