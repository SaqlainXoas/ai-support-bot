#core/tools.py

from langchain.tools import tool, StructuredTool
from pydantic import BaseModel, Field
from typing import Dict, Any
import logging
import asyncio
from server.services import WeatherService, CalendarService, WebSearchService
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

# Initialize services
weather_service = WeatherService()
calendar_service = CalendarService()
web_search_service = WebSearchService()

# Input schemas
class GetWeatherInput(BaseModel):
    city: str = Field(..., description="City name to get weather for")

class ScheduleEventInput(BaseModel):
    title: str = Field(..., description="Event title")
    start_time: str = Field(..., description="Start time in ISO format")
    duration: int = Field(..., description="Duration in minutes")

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=3, description="Maximum number of results")

class EscalateInput(BaseModel):
    query: str = Field(..., description="User's original query")
    user_id: str = Field(..., description="User's ID")
    reason: str = Field(default="Escalation requested", description="Reason for escalation")
# core/tools.py (updated)

@tool(args_schema=GetWeatherInput)
async def get_weather(city: str) -> str:
    """Get current weather for a city."""
    try:
        logger.info(f"🌤️ Getting weather for: {city}")
        weather_data = await weather_service.get_weather(city)
        return f"""🌡️ Weather in {city}:
Temperature: {weather_data['main']['temp']}°C
Feels like: {weather_data['main']['feels_like']}°C
Humidity: {weather_data['main']['humidity']}%
Conditions: {weather_data['weather'][0]['description']}"""
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        return f"Could not get weather for {city}. Please try again later."

@tool(args_schema=ScheduleEventInput)
async def schedule_event(title: str, start_time: str, duration: int) -> str:
    """Schedule an event in Google Calendar."""
    try:
        event = await calendar_service.create_event(
            title=title,
            start_time=start_time,
            duration=duration
        )
        return f"""📅 Event scheduled successfully!
Title: {title}
Start: {start_time}
Duration: {duration} minutes
Link: {event.get('htmlLink')}"""
    except Exception as e:
        logger.error(f"Calendar API error: {str(e)}")
        return "Failed to schedule event. Please try again later."

@tool(args_schema=WebSearchInput)
async def web_search(query: str, max_results: int = 3) -> str:
    """Search the web using Tavily API."""
    try:
        results = await web_search_service.search(
            query=query,
            max_results=max_results
        )
        formatted_results = []
        
        # Handle Tavily API response structure
        for result in results['results'][:max_results]:
            formatted_results.append(f"""🔍 {result.get('title', 'No title')}
URL: {result.get('url', 'No URL')}
Summary: {result.get('content', result.get('snippet', 'No content available'))}
---""")
        
        if not formatted_results:
            return "No search results found."
            
        return "\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        logger.error(f"Search results structure: {results if 'results' in locals() else 'No results'}")
        return "Failed to perform web search. Please try again later."

@tool(args_schema=EscalateInput)
async def escalate_to_human(query: str, user_id: str, reason: str = "Escalation requested") -> str:
    """Escalate the conversation to a human support agent."""
    try:
        logger.info(f"🔔 Escalating to human for user {user_id}")
        logger.info(f"Reason: {reason}")
        logger.info(f"Original query: {query}")
        return f"""🚨 Escalated: {query}
User: {user_id}
Reason: {reason}"""
    except Exception as e:
        logger.error(f"Escalation error: {str(e)}")
        return "Failed to escalate to human support. Please try again later."

# Define the list of support tools
SUPPORT_TOOLS = [
    get_weather,
    schedule_event,
    web_search,
    escalate_to_human
]

class ToolExecutor:
    def __init__(self, tools):
        self.tools = {tool.name: tool for tool in tools}
        
    async def execute(self, tool_name: str, args: dict) -> str:
        logger.info(f"🔧 Executing tool: {tool_name}")
        if tool_name not in self.tools:
            logger.error(f"❌ Tool not found: {tool_name}")
            raise ValueError(f"Tool {tool_name} not found")
                
        tool = self.tools[tool_name]
        try:
            # Validate and convert arguments using the tool's schema
            validated_args = tool.args_schema(**args)
            result = await tool.ainvoke(validated_args.dict())
            logger.info(f"✅ Tool execution successful")
            return result
        except Exception as e:
            logger.error(f"❌ Tool error in {tool_name}: {str(e)}")
            return f"Error executing {tool_name}: {str(e)}"