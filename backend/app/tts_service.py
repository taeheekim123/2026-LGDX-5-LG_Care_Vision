from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from google.oauth2 import service_account


TRUTHY = {"1", "true", "yes", "on"}
DEFAULT_TTS_VOICE = "en-IN-Standard-A"


def google_tts_enabled() -> bool:
    return os.getenv("GOOGLE_TTS_ENABLED", "0").strip().lower() in TRUTHY


def google_tts_voice_name() -> str:
    return os.getenv("GOOGLE_TTS_VOICE_NAME", DEFAULT_TTS_VOICE).strip() or DEFAULT_TTS_VOICE


@lru_cache(maxsize=1)
def _tts_client():
    from google.cloud import texttospeech

    credentials_json = os.getenv("GOOGLE_TTS_CREDENTIALS_JSON", "").strip()
    if credentials_json:
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return texttospeech.TextToSpeechClient(credentials=credentials)
    return texttospeech.TextToSpeechClient()


def synthesize_google_tts_mp3(
    *,
    text: str,
    language_code: str = "en-IN",
    voice_name: str | None = None,
    speaking_rate: float = 0.92,
) -> bytes:
    if not google_tts_enabled():
        raise RuntimeError("Google TTS is disabled")

    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("TTS text is empty")
    if len(normalized_text) > 800:
        raise ValueError("TTS text is too long")

    selected_voice = voice_name or google_tts_voice_name()
    cache_dir = Path(os.getenv("GOOGLE_TTS_CACHE_DIR", "runtime_logs/tts_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(
        f"{language_code}|{selected_voice}|{speaking_rate}|{normalized_text}".encode("utf-8")
    ).hexdigest()
    cache_path = cache_dir / f"{cache_key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes()

    from google.cloud import texttospeech

    response = _tts_client().synthesize_speech(
        request={
            "input": texttospeech.SynthesisInput(text=normalized_text),
            "voice": texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=selected_voice,
            ),
            "audio_config": texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
            ),
        }
    )
    audio_content = bytes(response.audio_content)
    cache_path.write_bytes(audio_content)
    return audio_content
