# AI Support Bot  🤖

A Slack-based support bot that leverages an agent-based architecture to intelligently handle user queries by dynamically selecting and calling the appropriate APIs. Powered by GPT-4 and integrated with multiple services for enhanced functionality.

## Overview 🌟

The AI Support Bot is designed to:
- **Understand natural language** using GPT-4 and semantic matching with Ada embeddings
- **Dynamically route requests** to appropriate services via agent-based decision making
- **Integrate multiple APIs** including Google Calendar, Weather, and Web Search
- **Escalate complex issues** to human agents when needed
- **Enhance responses** using RAG (Retrieval-Augmented Generation)


---

## Features 🚀

| Category              | Capabilities                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| **Core Intelligence** | GPT-4 processing, Ada embeddings, Agent-based decision system              |
| **Integrations**      | Google Calendar scheduling, Live weather data, Real-time web search        |
| **Support Features**  | Human escalation workflow, RAG-enhanced knowledge retrieval                |
| **Infrastructure**    | Dockerized services, PostgreSQL with pgvector, LangChain integration       |

---

## Tech Stack 🛠️

| Component               | Technology Used                          |
|-------------------------|------------------------------------------|
| Language Model          | OpenAI GPT-4                             |
| Embeddings              | OpenAI Ada                               |
| Vector Database         | PostgreSQL + pgvector                    |
| APIs                    | Slack, Google Calendar, OpenWeatherMap   |
| Framework               | LangChain                                |
| Infrastructure          | Docker, Docker Compose                   |

---

## Project Demo 🎥

A demonstration of the AI Support Bot in action:

<div align="center">
  <a href="https://github.com/user-attachments/assets/480665b9-4ed7-4349-b306-033155843c95">
    <img src="https://github.com/user-attachments/assets/480665b9-4ed7-4349-b306-033155843c95" alt="Project Demo" width="600"/>
  </a>
</div>

## Prerequisites 📋

- Python 3.9+
- Docker & Docker Compose
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector)
- Slack workspace with admin access
- Google Cloud Platform account
- API keys for:
  - OpenAI
  - Slack
  - Google Calendar
  - Weather API

---

## Environment Setup

1. Clone the repository
```bash
git clone https://github.com/SaqlainXoas/ai-support-bot.git
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
