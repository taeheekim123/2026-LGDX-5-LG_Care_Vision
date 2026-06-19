from __future__ import annotations

from fastapi import APIRouter, Response

from ..schemas import TTSSynthesizeRequest
from ..tts_service import synthesize_google_tts_mp3


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    audio = synthesize_google_tts_mp3(
        text=request.text,
        language_code=request.language_code,
        voice_name=request.voice_name,
        speaking_rate=request.speaking_rate,
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
