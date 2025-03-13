from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from .calendar_interface import CalendarInterface


class GoogleCalendarService(CalendarInterface):
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = Credentials(**credentials)
        self.service = build("calendar", "v3", credentials=self.credentials)

    @staticmethod
    def get_auth_url(
        client_secrets_file: str, scopes: List[str], redirect_uri: str
    ) -> str:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        flow.redirect_uri = redirect_uri  # 여기에 redirect_uri 설정 추가
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    @staticmethod
    def get_credentials_from_code(
        client_secrets_file: str, scopes: List[str], code: str, redirect_uri: str
    ) -> Dict[str, str]:
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes, redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

    def get_events(self) -> List[Dict]:
        events_result = self.service.events().list(calendarId="primary").execute()
        return events_result.get("items", [])

    def create_event(self, event: Dict) -> None:
        self.service.events().insert(calendarId="primary", body=event).execute()

    def update_event(self, event_id: str, event: Dict) -> None:
        self.service.events().update(
            calendarId="primary", eventId=event_id, body=event
        ).execute()

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId="primary", eventId=event_id).execute()
