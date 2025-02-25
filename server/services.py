#server/services.py

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from tavily import Client
import os
import pickle
from datetime import datetime, timedelta
import aiohttp
import pytz
import logging
import asyncio
# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)


class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    async def get_weather(self, city: str):
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                raise Exception(f"Weather API error: {response.status}")

class CalendarService:
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    PORT = 58408  # Set fixed port
    
    def __init__(self):
        self.credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'credentials',
            'google_credentials.json'
        )
        self.token_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'credentials',
            'token.pickle'
        )
        self.creds = self._load_credentials()
        self.service = build('calendar', 'v3', credentials=self.creds)

    def _load_credentials(self):
        creds = None
        
        try:
            # Ensure credentials directory exists
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, 
                        self.SCOPES
                    )
                    # Use fixed port
                    creds = flow.run_local_server(
                        port=self.PORT,
                        prompt='consent',
                        access_type='offline'
                    )
                
                # Save the credentials
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

            return creds
            
        except Exception as e:
            logger.error(f"Calendar authentication failed: {str(e)}")
            raise

    async def create_event(self, title: str, start_time: str, duration: int):
        try:
            # Parse the start time
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            # Calculate end time using timedelta
            end = start + timedelta(minutes=duration)
            
            event = {
                'summary': title,
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': 'UTC'
                },
                'reminders': {
                    'useDefault': True
                }
            }
            
            result = await asyncio.to_thread(
                self.service.events().insert,
                calendarId='primary',
                body=event,
                sendUpdates='all'
            )
            return result.execute()
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {str(e)}")
            raise

class WebSearchService:
    def __init__(self):
        from tavily import TavilyClient
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    async def search(self, query: str, max_results: int = 3, search_depth="basic"):
        try:
            # Note: Tavily's search might be synchronous
            result = await asyncio.to_thread(
                self.client.search,
                query=query,
                search_depth=search_depth,
                # Remove max_results from here as it's not supported by Tavily API
            )
            # Instead, limit results after receiving them
            if 'results' in result:
                result['results'] = result['results'][:max_results]
            return result
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'results': []
            }