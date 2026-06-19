from __future__ import annotations

import re
import shutil
from typing import Any

from fastapi.testclient import TestClient

from app.dependencies import get_service
from app.main import app
from app.repositories import CareShotRepository
from app.repositories.database import DEFAULT_SQLITE_DB_PATH
from app.services import CareShotBackendService


KOREAN_RE = re.compile(r"[가-힣]")


def make_test_client(tmp_path):
    test_db = tmp_path / "careshot_ar_mock.db"
    shutil.copy2(DEFAULT_SQLITE_DB_PATH, test_db)
    service = CareShotBackendService()
    service.repo = CareShotRepository(test_db)
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)


def iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def assert_no_korean_text(value: Any, *, context: str) -> None:
    offenders = [text for text in iter_strings(value) if KOREAN_RE.search(text)]
    assert offenders == [], f"{context} contains Korean text: {offenders[:5]}"


def test_guide_options_display_steps_are_english_only(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        for procedure_type, service_flow_type in [
            ("filter_cleaning", "self_care"),
            ("no_cooling_self_check", "self_as"),
        ]:
            response = client.get(
                "/api/v1/guides/options",
                params={
                    "user_id": "U001",
                    "device_id": "D001",
                    "procedure_type": procedure_type,
                    "service_flow_type": service_flow_type,
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["language_code"] == "en"
            assert payload["display_title"]
            assert payload["display_steps"]
            for step in payload["display_steps"]:
                assert step["language_code"] == "en"
                assert step["source_language_code"] == "en"
            assert_no_korean_text(payload["display_title"], context=f"{procedure_type} display_title")
            assert_no_korean_text(payload["display_steps"], context=f"{procedure_type} display_steps")
    finally:
        app.dependency_overrides.clear()


def test_ar_plan_tts_and_visible_step_copy_are_english_only(tmp_path) -> None:
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
        assert response.status_code == 200
        payload = response.json()
        steps = payload["ar_overlay_data"]["guide_steps"]
        assert steps
        for step in steps:
            assert step["tts_language_code"] == "en-IN"
            assert step["tts_provider"] == "web_speech"
            assert step["next_button_label"] in {"Next", "Complete"}
            visible_step_payload = {
                "display_title": step.get("display_title"),
                "display_instruction": step.get("display_instruction"),
                "display_safety": step.get("display_safety"),
                "next_button_label": step.get("next_button_label"),
                "tts_text": step.get("tts_text"),
            }
            assert_no_korean_text(visible_step_payload, context="AR plan visible step payload")
    finally:
        app.dependency_overrides.clear()


def test_frontend_chat_compat_visible_response_is_english_only(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "필터 청소 방법 알려줘",
                "context": {"deviceId": "D001"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        visible_payload = {
            "message": payload.get("message"),
            "card_policy": payload.get("card_policy"),
            "guide_options_display_title": (payload.get("guide_options") or {}).get("display_title"),
            "guide_options_display_steps": (payload.get("guide_options") or {}).get("display_steps"),
        }
        assert payload["card_policy"]["title"] == "AR guide available"
        assert_no_korean_text(visible_payload, context="frontend chat visible response")
    finally:
        app.dependency_overrides.clear()


def test_care_risk_visible_reasons_are_english_only(tmp_path) -> None:
    client = make_test_client(tmp_path)
    try:
        response = client.post(
            "/api/v1/care/risk/evaluate",
            json={"user_id": "U001", "device_id": "D001"},
        )
        assert response.status_code == 200
        payload = response.json()
        visible_payload = {
            "care_risk_score": payload.get("care_risk_score"),
            "care_risk_decision_factor_scores": (payload.get("care_risk_decision") or {}).get("factor_scores"),
            "recommendation": payload.get("recommendation"),
        }
        assert_no_korean_text(visible_payload, context="care risk visible response")
    finally:
        app.dependency_overrides.clear()
