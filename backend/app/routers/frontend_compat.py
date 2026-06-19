from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_service
from ..services import CareShotBackendService


router = APIRouter(tags=["frontend-compat"])


def _frontend_user_profile(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw or {}
    user_email = raw.get("user_email") or raw.get("email") or raw.get("user_id") or "u001@careshot.local"
    name = (
        raw.get("customer_name")
        or raw.get("user_name")
        or raw.get("display_name")
        or raw.get("name")
        or "तनीषा"
    )
    phone = raw.get("phone_number") or raw.get("phone") or "+91-9876543210"
    city = raw.get("city") or "New Delhi"
    region = raw.get("region") or raw.get("state") or "Delhi"
    country = raw.get("country") or "India"
    address = raw.get("address") or raw.get("address_line1") or f"{country} {region} {city}"
    return {
        "user_email": str(user_email),
        "email": str(user_email),
        "name": str(name),
        "phone": str(phone),
        "address": str(address),
        "region_id": str(raw.get("region_id") or ""),
        "region": str(region),
        "city": str(city),
    }


def _frontend_device_option(raw: dict[str, Any] | None, fallback_id: str) -> dict[str, Any]:
    raw = raw or {}
    device_id = raw.get("device_id") or fallback_id
    name = raw.get("display_name") or raw.get("nickname") or raw.get("product_name") or "Living Room Air Conditioner"
    if name == "거실 에어컨":
        name = "Living Room Air Conditioner"
    model = raw.get("model_name") or raw.get("model") or "AS-Q24ENXE"
    return {"id": str(device_id), "name": str(name), "model": str(model)}


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _relative_date_label(value: Any) -> str:
    parsed = _parse_datetime(value)
    if not parsed:
        return ""
    now = datetime.now(timezone.utc)
    days = max(0, int((now - parsed.astimezone(timezone.utc)).total_seconds() // 86400))
    if days <= 0:
        return "Today"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} weeks ago"
    months = days // 30
    return f"{max(months, 1)} months ago"


def _care_history_title(item: dict[str, Any]) -> str:
    raw_title = item.get("title")
    procedure = item.get("procedure_type") or raw_title
    labels = {
        "ar_guide": "Air conditioner filter cleaning",
        "filter_cleaning": "Air conditioner filter cleaning",
        "remote_pairing": "Remote pairing",
        "remote_operation": "Remote operation check",
        "outdoor_unit_visual_check": "Outdoor unit visual check",
        "power_troubleshooting": "Power self-check",
        "no_cooling_self_check": "Weak cooling/airflow self-check",
        "noise_self_check": "Noise/vibration self-check",
        "odor_self_check": "Odor self-check",
        "water_leak_monsoon": "Water leak self-check",
    }
    return labels.get(str(procedure), str(raw_title or procedure or "Care history"))


def _frontend_care_history_item(item: dict[str, Any]) -> dict[str, str]:
    completed_at = item.get("completed_at") or item.get("started_at")
    service_flow_type = item.get("service_flow_type") or "self_care"
    return {
        "id": str(item.get("history_id") or ""),
        "type": "Self A/S" if service_flow_type == "self_as" else "Self Care",
        "title": _care_history_title(item),
        "date": _relative_date_label(completed_at),
    }


def _frontend_device_care_payload(
    service: CareShotBackendService,
    user_id: str,
    device_id: str,
) -> dict[str, Any]:
    care_history = service.get_device_care_history(user_id=user_id, device_id=device_id, limit=3)
    if not care_history:
        return {
            "care_summary": {
                "self_care_count": 0,
                "self_as_count": 0,
                "total_care_count": 0,
                "recent_title": "",
                "recent_date": "",
            },
            "recent_history": [],
        }

    items = [_frontend_care_history_item(item) for item in care_history.get("items", [])]
    summary = care_history.get("summary") or {}
    first = items[0] if items else {}
    return {
        "care_summary": {
            "self_care_count": int(summary.get("self_care_count") or 0),
            "self_as_count": int(summary.get("self_as_count") or 0),
            "total_care_count": int(summary.get("total_care_count") or 0),
            "recent_title": first.get("title", ""),
            "recent_date": first.get("date", ""),
        },
        "recent_history": items,
    }


def _message_from_payload(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        return str(message.get("content") or message.get("text") or "")
    return str(payload.get("content") or payload.get("text") or "")


def _json_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else []
    return []


def _symptom_location_question(procedure: str | None) -> str:
    return {
        "noise_self_check": "Where do you notice the noise or vibration? Please choose the closest area, such as the indoor unit body, air outlet, front cover, drain area, or power area.",
        "no_cooling_self_check": "Please tell me more about the weak cooling condition. Is air coming out, is the airflow weak, or does it seem related to the air outlet?",
        "power_troubleshooting": "Please tell me more about the power issue. Do you notice anything unusual with the plug, outlet, breaker, display, or remote controller?",
        "odor_self_check": "Where is the odor strongest? Please choose the closest area, such as the air outlet, filter, indoor unit body, or drain area.",
        "water_leak_monsoon": "Where is the water leaking from? Please choose the closest area, such as the indoor unit body, air outlet, drain hose, or outdoor unit area.",
    }.get(str(procedure), "Please tell me more about where or when the symptom appears.")


def _localized_chat_message(raw: dict[str, Any], fallback: str) -> str:
    chatbot = raw.get("chatbot_engine") or {}
    state = chatbot.get("conversation_state") or {}
    analysis = raw.get("analysis") or {}
    decision = analysis.get("decision_result") or {}
    procedure = (analysis.get("procedure") or {}).get("procedure_type")
    missing_slots = _json_list(state.get("missing_slots") or decision.get("missing_slots"))

    if missing_slots:
        first_missing = missing_slots[0]
        if first_missing == "risk_signal":
            return "Do you notice any danger signs such as smoke, sparks, burning smell, electric shock, or refrigerant/gas odor? If not, please answer 'No'."
        if first_missing == "symptom_location":
            return _symptom_location_question(procedure)
        if first_missing == "environment_context":
            return "Is the room currently humid, dusty, or affected by rain or monsoon conditions?"
        if first_missing == "recent_diagnosis":
            return "Do you see an error code in ThinQ diagnosis or on the display? Also tell me if the breaker trips or power turns off repeatedly."
        if first_missing == "symptom_type":
            return "What issue are you experiencing? Please choose the closest symptom: cooling/airflow, noise/vibration, odor, water leak, power issue, or filter care."
        return "Please share one more detail so I can guide you safely."

    if decision.get("service_flow_type") == "expert_as" or decision.get("risk_level") == "high":
        return "A danger sign was detected, so AR self-guidance is blocked. We recommend official service or service center support."

    procedure_label = {
        "filter_cleaning": "filter cleaning",
        "noise_self_check": "noise/vibration self-check",
        "no_cooling_self_check": "weak cooling/airflow self-check",
        "odor_self_check": "odor self-check",
        "water_leak_monsoon": "water leak self-check",
        "power_troubleshooting": "power self-check",
    }.get(str(procedure), "guide")
    if chatbot.get("guide_options"):
        return f"I prepared an official-evidence-based {procedure_label}. Only steps allowed by the safety policy will be shown."
    return fallback


def _frontend_card_policy(raw: dict[str, Any]) -> dict[str, Any]:
    chatbot = raw.get("chatbot_engine") or {}
    analysis = raw.get("analysis") or {}
    decision = analysis.get("decision_result") or {}
    state = chatbot.get("conversation_state") or {}
    guide_options = chatbot.get("guide_options")
    missing_slots = _json_list(state.get("missing_slots") or decision.get("missing_slots"))
    service_flow_type = decision.get("service_flow_type")
    risk_level = decision.get("risk_level")
    decision_action = decision.get("decision_action")
    blocked_reason = decision.get("blocked_reason")
    ar_guide_allowed = bool(decision.get("ar_guide_allowed"))
    official_match = analysis.get("official_asset_match") or {}
    official_match_status = official_match.get("match_status")
    no_match_actions = {"official_match_review_needed", "official_evidence_required"}

    if missing_slots:
        return {
            "card_type": "clarification",
            "title": "More information needed",
            "description": "Please answer the safety question before guidance starts.",
            "primary_action": "answer_question",
            "show_manual_button": False,
            "show_ar_button": False,
            "show_service_button": False,
            "reason": "missing_slots",
        }

    if service_flow_type == "expert_as" or risk_level == "high":
        return {
            "card_type": "service_route",
            "title": "Expert service recommended",
            "description": "A danger sign was detected, so AR self-guidance is blocked and only service center support is provided.",
            "primary_action": "service_center",
            "show_manual_button": False,
            "show_ar_button": False,
            "show_service_button": True,
            "reason": blocked_reason or "high_risk",
        }

    if decision_action in no_match_actions or (
        official_match_status is not None and official_match_status != "verified"
    ):
        return {
            "card_type": "safety_block",
            "title": "Official evidence unavailable",
            "description": "AR self-guidance will not start because official evidence was not verified.",
            "primary_action": "service_center",
            "show_manual_button": False,
            "show_ar_button": False,
            "show_service_button": True,
            "reason": blocked_reason or decision_action or "official_no_match",
        }

    if guide_options and service_flow_type in {"self_care", "self_as"} and risk_level in {"low", "medium"}:
        return {
            "card_type": "ar_start",
            "title": "AR guide available",
            "description": "This is an official-evidence-based low/medium-risk self-check or care guide.",
            "primary_action": "start_ar",
            "show_manual_button": True,
            "show_ar_button": True,
            "show_service_button": False,
            "reason": "official_guide_options_ready",
        }

    if guide_options:
        return {
            "card_type": "manual_only",
            "title": "Manual guide available",
            "description": "An official-material-based manual guide is available first.",
            "primary_action": "manual_guide",
            "show_manual_button": True,
            "show_ar_button": ar_guide_allowed,
            "show_service_button": False,
            "reason": "manual_guide_options_ready",
        }

    return {
        "card_type": "none",
        "title": "",
        "description": "",
        "primary_action": None,
        "show_manual_button": False,
        "show_ar_button": False,
        "show_service_button": False,
        "reason": "no_display_card",
    }


def _frontend_ai_chat_response(raw: dict[str, Any]) -> dict[str, Any]:
    chatbot = raw.get("chatbot_engine") or {}
    ai_message = chatbot.get("ai_message") or {}
    analysis = raw.get("analysis") or {}
    decision = analysis.get("decision_result") or {}
    state = chatbot.get("conversation_state") or {}
    guide_options = chatbot.get("guide_options")
    missing_slots = _json_list(state.get("missing_slots") or decision.get("missing_slots"))
    fallback_message = (
        ai_message.get("message_content")
        or state.get("next_question")
        or "I checked your request."
    )

    return {
        "message": _localized_chat_message(raw, fallback_message),
        "message_type": ai_message.get("message_type") or "text",
        "session_id": (raw.get("chat_session") or {}).get("session_id") or state.get("session_id"),
        "intent": decision.get("intent_type") or decision.get("service_flow_type"),
        "service_flow_type": decision.get("service_flow_type"),
        "risk_level": decision.get("risk_level"),
        "procedure_type": (analysis.get("procedure") or {}).get("procedure_type"),
        "recommended_action": decision.get("decision_action"),
        "needs_clarification": bool(missing_slots),
        "missing_slots": missing_slots,
        "guide_options": guide_options,
        "card_policy": _frontend_card_policy(raw),
        "analysis": analysis,
        "raw": raw,
    }


@router.post("/users/register", status_code=status.HTTP_201_CREATED)
def register_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.register_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "user": _frontend_user_profile(profile),
        "demo_seed": profile.get("demo_seed") or {},
    }


@router.post("/users/login")
def login_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.login_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return {"user": _frontend_user_profile(profile)}


@router.get("/users/me")
def get_current_frontend_user(
    user_email: str | None = None,
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, str]:
    return _frontend_user_profile(service.repo.get_user_profile(user_email or "U001"))


@router.put("/users/me")
def update_frontend_user(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    try:
        profile = service.update_frontend_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"user": _frontend_user_profile(profile)}


@router.get("/devices")
def get_frontend_devices(
    user_id: str = "U001",
    service: CareShotBackendService = Depends(get_service),
) -> list[dict[str, Any]]:
    primary = service.repo.get_device_context("D001")
    if primary:
        device = _frontend_device_option(primary, "D001")
    else:
        device = {"id": "D001", "name": "Living Room Air Conditioner", "model": "AS-Q24ENXE"}
    device.update(_frontend_device_care_payload(service, user_id, str(device["id"])))
    return [device]


@router.get("/devices/{device_id}")
def get_frontend_device_detail(
    device_id: str,
    user_id: str = "U001",
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    primary = service.repo.get_device_context(device_id)
    if not primary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    device = _frontend_device_option(primary, device_id)
    device.update(_frontend_device_care_payload(service, user_id, str(device["id"])))
    return device


@router.post("/chat-messages", status_code=status.HTTP_201_CREATED)
def save_frontend_chat_message(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "saved": True,
        "message": payload.get("message") or payload,
        "storage": "frontend_compat_ack",
    }


@router.post("/ai/chat")
def request_frontend_ai_chat(
    payload: dict[str, Any],
    service: CareShotBackendService = Depends(get_service),
) -> dict[str, Any]:
    message = _message_from_payload(payload).strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")

    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    request = {
        "user_id": payload.get("user_id") or context.get("user_id") or "U001",
        "device_id": payload.get("device_id") or context.get("deviceId") or context.get("device_id") or "D001",
        "session_id": payload.get("session_id") or context.get("session_id"),
        "message": message,
        "include_rag_evidence": bool(payload.get("include_rag_evidence", True)),
    }
    return _frontend_ai_chat_response(service.process_chat_message(request))
