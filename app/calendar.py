from typing import Any

import httpx

from app.config import settings


async def get_availability(from_time: str, to_time: str) -> dict[str, Any]:
    if settings.calendar_provider != "calcom":
        return {"slots": [], "message": "Calendar provider is not configured."}
    if not settings.calcom_api_key or not settings.calcom_event_type_id:
        return {"slots": [], "message": "Cal.com credentials are missing."}

    params = {
        "apiKey": settings.calcom_api_key,
        "eventTypeId": settings.calcom_event_type_id,
        "startTime": from_time,
        "endTime": to_time,
        "timeZone": settings.calcom_timezone,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://api.cal.com/v1/slots", params=params)
    if response.status_code >= 400:
        return {"slots": [], "message": "Calendar availability check failed."}
    data = response.json()
    return {"slots": data.get("slots", data), "message": "Availability loaded."}


async def book_meeting(name: str, email: str, start: str, notes: str = "") -> dict[str, Any]:
    if not name or not email or not start:
        return {"ok": False, "error": "Name, email, and preferred start time are required."}
    if settings.calendar_provider != "calcom":
        return {"ok": False, "error": "Calendar provider is not configured."}
    if not settings.calcom_api_key or not settings.calcom_event_type_id:
        return {"ok": False, "error": "Cal.com credentials are missing, so I cannot confirm a real meeting yet."}

    payload = {
        "eventTypeId": int(settings.calcom_event_type_id),
        "start": start,
        "responses": {"name": name, "email": email, "notes": notes},
        "timeZone": settings.calcom_timezone,
        "language": "en",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.cal.com/v1/bookings",
            params={"apiKey": settings.calcom_api_key},
            json=payload,
        )
    if response.status_code >= 400:
        return {"ok": False, "error": f"Booking failed: {response.text[:300]}"}
    return {
        "ok": True,
        "message": "Meeting confirmed. Calendar invitation should arrive by email.",
        "booking": response.json(),
    }
