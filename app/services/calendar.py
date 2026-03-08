import json
from typing import List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

class GoogleCalendarService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = ['https://www.googleapis.com/auth/calendar.events']
        self.creds: Credentials | None = None

    def get_auth_url(self) -> str:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uris": [self.redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        return auth_url

    async def exchange_code(self, code: str):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uris": [self.redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        flow.fetch_token(code=code)
        self.creds = flow.credentials

    async def create_event(self, summary: str, start: str, end: str, attendees: List[str]):
        if not self.creds:
            raise ValueError("Não autenticado no Google Calendar")
        service = build('calendar', 'v3', credentials=self.creds)
        body = {
            'summary': summary,
            'start': {'dateTime': start},
            'end': {'dateTime': end},
            'attendees': [{'email': a} for a in attendees],
        }
        event = service.events().insert(calendarId='primary', body=body).execute()
        return event