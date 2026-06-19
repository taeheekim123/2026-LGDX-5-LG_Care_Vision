from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1]
TTS_CACHE_DIR = BACKEND_DIR / "runtime_logs" / "tts_cache"


def google_tts_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def google_tts_voice_name(language_code: str, requested_voice_name: str | None = None) -> str | None:
    if requested_voice_name:
        return requested_voice_name
    configured = os.getenv("GOOGLE_TTS_VOICE_NAME", "").strip()
    if configured:
        return configured
    if language_code == "en-IN":
        return "en-IN-Standard-A"
    return None


def _credentials_from_env() -> Any:
    credentials_json = os.getenv("GOOGLE_TTS_CREDENTIALS_JSON", "").strip()
    if not credentials_json:
        return None
    try:
        from google.oauth2 import service_account

        info = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    except Exception as exc:  # pragma: no cover - exact auth exceptions vary by google-auth version
        raise HTTPException(status_code=500, detail="Invalid Google TTS credentials JSON") from exc


def _client():
    try:
        from google.cloud import texttospeech
    except Exception as exc:  # pragma: no cover - import failure is environment-dependent
        raise HTTPException(status_code=503, detail="Google TTS client library is not installed") from exc

    credentials = _credentials_from_env()
    if credentials is not None:
        return texttospeech.TextToSpeechClient(credentials=credentials), texttospeech
    return texttospeech.TextToSpeechClient(), texttospeech


def _cache_path(*, text: str, language_code: str, voice_name: str | None, speaking_rate: float) -> Path:
    material = json.dumps(
        {
            "text": text,
            "language_code": language_code,
            "voice_name": voice_name,
            "speaking_rate": round(speaking_rate, 3),
            "encoding": "MP3",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return TTS_CACHE_DIR / f"{digest}.mp3"


def synthesize_google_tts_mp3(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> bytes:
    clean_text = " ".join((text or "").split())
    if not clean_text:
        raise HTTPException(status_code=422, detail="TTS text is empty")
    if len(clean_text) > 800:
        raise HTTPException(status_code=422, detail="TTS text is too long")
    if not google_tts_enabled():
        raise HTTPException(status_code=503, detail="Google TTS is disabled")

    resolved_voice_name = google_tts_voice_name(language_code, voice_name)
    TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(
        text=clean_text,
        language_code=language_code,
        voice_name=resolved_voice_name,
        speaking_rate=speaking_rate,
    )
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes()

    client, texttospeech = _client()
    voice_kwargs: dict[str, Any] = {"language_code": language_code}
    if resolved_voice_name:
        voice_kwargs["name"] = resolved_voice_name

    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=clean_text),
        voice=texttospeech.VoiceSelectionParams(**voice_kwargs),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
        ),
    )
    audio_content = bytes(response.audio_content)
    if not audio_content:
        raise HTTPException(status_code=502, detail="Google TTS returned empty audio")
    cache_path.write_bytes(audio_content)
    return audio_content
