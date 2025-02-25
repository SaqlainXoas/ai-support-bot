# slack_handler.py 

import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import sys
import os
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from core.agents import workflow
from dotenv import load_dotenv
import asyncio
from server.services import CalendarService
import re
from datetime import datetime, timedelta
import pytz

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))
compiled_workflow = workflow.compile()
calendar_service = CalendarService()

def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime."""
    time_str = time_str.lower().strip()
    if 'pm' in time_str:
        time_str = time_str.replace('pm', '').strip()
        hour = int(time_str.split(':')[0])
        if hour != 12:
            hour += 12
        time_str = f"{hour}:00"
    elif 'am' in time_str:
        time_str = time_str.replace('am', '').strip()
        hour = int(time_str.split(':')[0])
        if hour == 12:
            hour = 0
        time_str = f"{hour:02d}:00"
    else:
        hour = int(time_str.split(':')[0])
        time_str = f"{hour:02d}:00"
    
    return datetime.strptime(time_str, '%H:%M')

@app.event("app_mention")
async def handle_message(event, say):
    try:
        auth_test_result = await app.client.auth_test()
        bot_user_id = auth_test_result['user_id']
        text = event.get("text", "").replace(f"<@{bot_user_id}>", "").strip()
        
        # Check for calendar-related commands
        if "schedule" in text.lower() and "meeting" in text.lower():
            # Basic parsing for meeting details
            time_match = re.search(r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', text, re.IGNORECASE)
            duration_match = re.search(r'for (\d+)\s*(?:hour|hr|minute|min)', text, re.IGNORECASE)
            
            if time_match and duration_match:
                try:
                    # Parse time
                    time_str = time_match.group(1)
                    duration = int(duration_match.group(1))
                    
                    # Convert time string to datetime
                    time_obj = parse_time(time_str)
                    start_time = datetime.combine(datetime.now().date(), time_obj.time())
                    
                    # Add timezone info
                    start_time = pytz.UTC.localize(start_time)
                    
                    result = await calendar_service.create_event(
                        title="Team Meeting",
                        start_time=start_time.isoformat(),
                        duration=duration
                    )
                    await say(f"✅ Meeting scheduled! View details: {result['htmlLink']}")
                    return
                except Exception as e:
                    logger.error(f"Failed to schedule meeting: {str(e)}")
                    await say(f"❌ Failed to schedule meeting: {str(e)}")
                    return
        
        # Continue with regular workflow for non-calendar requests
        initial_state = {
            "query": text,
            "user_id": event.get("user", ""),
            "intermediate_steps": [],
            "context": [],
            "response": "",
            "needs_escalation": False,
            "tool_outputs": [],
            "escalation_reason": None,
            "tool_calls": None
        }
        
        # Execute workflow
        state = await compiled_workflow.ainvoke(initial_state)
        await say(state.get("response", "No response generated."))
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}", exc_info=True)
        await say("An error occurred while processing your request.")

async def main():
    handler = AsyncSocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    logger.info("Starting Slack handler...")
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())
