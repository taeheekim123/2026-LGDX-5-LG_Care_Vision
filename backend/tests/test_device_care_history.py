from __future__ import annotations

import shutil
import sqlite3

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    with sqlite3.connect(test_db) as conn:
        conn.execute('DELETE FROM "SELF_MANAGEMENT_HISTORY"')
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app), service


def test_device_care_history_reads_final_self_management_history_shape(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        response = client.get("/api/v1/devices/D001/care-history?user_id=U001")
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == "U001"
        assert payload["device_id"] == "D001"
        assert payload["summary"]["self_care_count"] == 0
        assert payload["summary"]["self_as_count"] == 0
        assert payload["summary"]["total_care_count"] == 0
        assert payload["items"] == []
    finally:
        app.dependency_overrides.clear()


def test_device_care_history_filters_and_handles_missing_device(tmp_path) -> None:
    client, _service = make_test_client(tmp_path)
    try:
        self_as_response = client.get(
            "/api/v1/devices/D001/care-history",
            params={"user_id": "U001", "service_flow_type": "self_as", "limit": 10},
        )
        assert self_as_response.status_code == 200
        assert self_as_response.json()["items"] == []

        missing_response = client.get("/api/v1/devices/UNKNOWN_DEVICE/care-history?user_id=U001")
        assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_device_care_history_counts_self_care_and_self_as_from_db(tmp_path) -> None:
    client, service = make_test_client(tmp_path)
    with sqlite3.connect(service.repo.db_path) as conn:
        rows = [
            (1, "AS-Q24ENXE", "u001@careshot.local", "filter_cleaning", "self_care", "2026-06-15T00:00:00+00:00"),
            (2, "AS-Q24ENXE", "u001@careshot.local", "remote_pairing", "self_as", "2026-06-08T00:00:00+00:00"),
            (3, "AS-Q24ENXE", "u001@careshot.local", "outdoor_unit_visual_check", "self_care", "2026-06-01T00:00:00+00:00"),
            (4, "AS-Q24ENXE", "u001@careshot.local", "no_cooling_self_check", "self_as", "2026-05-30T00:00:00+00:00"),
            (5, "AS-Q24ENXE", "u001@careshot.local", "odor_self_check", "self_care", "2026-05-20T00:00:00+00:00"),
            (6, "AS-Q24ENXE", "u001@careshot.local", "filter_cleaning", "self_care", "2026-05-10T00:00:00+00:00"),
            (7, "AS-Q24ENXE", "u001@careshot.local", "water_leak_monsoon", "self_care", "2026-05-01T00:00:00+00:00"),
        ]
        conn.executemany(
            """
            INSERT INTO "SELF_MANAGEMENT_HISTORY" (
              history_id, product_code, user_email, management_category, management_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    try:
        response = client.get("/api/v1/devices/D001/care-history", params={"user_id": "U001", "limit": 3})
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["self_care_count"] == 5
        assert payload["summary"]["self_as_count"] == 2
        assert payload["summary"]["total_care_count"] == 7
        assert [item["service_flow_type"] for item in payload["items"]] == [
            "self_care",
            "self_as",
            "self_care",
        ]
        assert [item["procedure_type"] for item in payload["items"]] == [
            "filter_cleaning",
            "remote_pairing",
            "outdoor_unit_visual_check",
        ]
    finally:
        app.dependency_overrides.clear()
