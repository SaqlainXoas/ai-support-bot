# AI Support Bot

A Slack-based support bot using RAG (Retrieval-Augmented Generation) and LangChain for intelligent customer support.

## Features

- 🤖 Intelligent query handling with GPT-4
- 📚 RAG-based knowledge retrieval
- 🗓️ Google Calendar integration
- 🌤️ Weather information
- 🔍 Web search capabilities
- 📈 Automatic escalation system

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL with pgvector
- Slack Workspace Admin access
- Google Cloud Platform account

## Environment Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/ai-support-bot.git
cd ai-support-bot
```

2. Create virtual environment
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure credentials
- Copy `.env.example` to `.env`
- Set up Google Calendar API credentials
- Configure Slack bot tokens
- Add other API keys

5. Start PostgreSQL database
```bash
docker-compose up -d
```

6. Run data ingestion
```bash
python data/ingest.py
```

7. Start the bot
```bash
python -m server.slack_handler
```

## Configuration Files

### Environment Variables
Create `.env` file with required credentials:
```env
OPENAI_API_KEY=your_key
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token
DB_URL=postgresql://admin:admin@localhost:5432/support_db
```

### Google Calendar Setup
1. Create project in Google Cloud Console
2. Enable Calendar API
3. Create OAuth credentials
4. Save as `credentials/google_credentials.json`

## Directory Structure
```
ai-support-bot/
├── .env
├── docker-compose.yml
├── requirements.txt
├── credentials/
├── server/
├── core/
└── data/
```

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License
MIT License