from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..schemas import TTSSynthesizeRequest
from ..tts_service import synthesize_google_tts_mp3


router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("/synthesize")
def synthesize_tts(request: TTSSynthesizeRequest) -> Response:
    try:
        audio = synthesize_google_tts_mp3(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice_name,
            speaking_rate=request.speaking_rate,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google TTS request failed: {exc}") from exc

    return Response(content=audio, media_type="audio/mpeg")
