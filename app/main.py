from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from app.calendar import book_meeting, get_availability
from app.config import settings
from app.llm import answer_with_evidence
from app.rag import retrieve


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]


class BookingRequest(BaseModel):
    name: str
    email: EmailStr
    start: str
    notes: str = ""
    source: str = "unknown"


class VoiceRequest(BaseModel):
    message: str | None = None
    transcript: str | None = None
    query: str | None = None


app = FastAPI(title="AI Persona Interview Agent")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "persona": settings.persona_name}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    latest = request.messages[-1]["content"] if request.messages else ""
    evidence = retrieve(latest)
    return await answer_with_evidence(request.messages, evidence)


@app.get("/api/availability")
async def availability(
    from_time: str | None = Query(default=None, alias="from"),
    to_time: str | None = Query(default=None, alias="to"),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = from_time or now.isoformat()
    end = to_time or (now + timedelta(days=14)).isoformat()
    return await get_availability(start, end)


@app.post("/api/book")
async def book(request: BookingRequest) -> dict[str, Any]:
    result = await book_meeting(request.name, request.email, request.start, request.notes)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Booking failed."))
    return result


@app.post("/api/voice/respond")
async def voice_respond(
    request: VoiceRequest,
    x_voice_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    if settings.voice_webhook_secret and x_voice_secret != settings.voice_webhook_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    text = request.message or request.transcript or request.query or ""
    evidence = retrieve(text, limit=4)
    answer = await answer_with_evidence([{"role": "user", "content": text}], evidence, voice=True)
    return {"response": answer["answer"], "sources": answer["sources"]}


public_dir = Path("public")
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
