import os
from fastapi import APIRouter, HTTPException
from ..services.calendar import GoogleCalendarService

router = APIRouter()

gcal = GoogleCalendarService(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    redirect_uri=os.getenv("GOOGLE_REDIRECT_URI"),
)

@router.get('/auth-url')
async def get_auth_url():
    return {"url": gcal.get_auth_url()}

@router.get('/callback')
async def callback(code: str):
    try:
        await gcal.exchange_code(code)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/create-event')
async def create_event(summary: str, start: str, end: str, attendees: list[str] | None = None):
    try:
        event = await gcal.create_event(summary, start, end, attendees or [])
        return {"event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))