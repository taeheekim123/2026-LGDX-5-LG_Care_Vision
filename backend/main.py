from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="LG Care Shot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    message = req.message.strip()
    lower_message = message.lower()

    if "filter" in lower_message or "필터" in message:
        return {
            "reply": "필터 상태를 확인했어요. 전원을 끄고 필터 커버를 연 뒤, 필터를 분리해 물로 세척하고 완전히 건조한 후 다시 장착해 주세요.",
            "showVideo": True,
            "guideButtons": ["manual", "ar"],
        }

    if "cooling" in lower_message or "not cooling" in lower_message or "냉방" in message:
        return {
            "reply": "냉방 문제가 감지됐어요. 필터 먼지, 실외기 주변 장애물, 설정 온도를 먼저 확인해 주세요.",
            "problemOptions": [
                "전원이 불안정하거나 자주 꺼져요",
                "실외기 주변이 막혀 있어요",
                "필터에 먼지가 많이 쌓여 있어요",
                "다른 문제가 있어요",
            ],
        }

    if "as" in lower_message or "service" in lower_message or "서비스" in message:
        return {
            "reply": "방문 A/S가 필요할 수 있어요. 가까운 LG전자 서비스센터 정보를 안내해드릴게요.",
            "serviceCenter": {
                "name": "LG전자 서비스센터",
                "address": "서울특별시 강남구 테헤란로 123",
                "phone": "1544-7777",
            },
        }

    return {
        "reply": f"백엔드에서 받은 메시지예요: {message}\n제품 문제, 필터 청소, A/S 문의를 도와드릴 수 있어요.",
    }
