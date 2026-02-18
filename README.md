# 🎙️ Voice AI Platform

**Complete voice AI assistant platform. Share a link → users talk to your AI → transcripts saved to database.**

Perfect for customer support, medical offices, real estate, education, and any business that needs voice AI.

## Features

- 🔗 **Shareable links** — `/talk/your-assistant` anyone can use
- 🎤 **Real-time voice chat** — STT → AI → TTS pipeline (sub-2s)
- 📝 **Full transcripts** — Every conversation stored and searchable
- 👥 **Multi-tenant** — Unlimited assistants per account
- 🧠 **Custom knowledge** — Upload docs, FAQ, context
- 🎭 **20+ voices** — ElevenLabs multilingual voices
- 📊 **Analytics** — Conversations, messages, stats
- 🔌 **Embeddable widget** — One `<script>` tag on any website
- 🐳 **Docker ready** — One command deployment
- 💳 **Stripe hooks** — Subscription billing ready

## Quick Start

```bash
# 1. Setup
chmod +x setup.sh && ./setup.sh

# 2. Edit .env with your API keys
nano .env

# 3. Run
source venv/bin/activate
python3 main.py

# 4. Open http://localhost:8000/docs
```

## Docker

```bash
cp .env.example .env
# Edit .env
docker-compose up -d
```

## Usage

```bash
# Create account
curl -X POST http://localhost:8000/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{"name":"My Company","email":"me@example.com"}'
# Returns: {"api_key": "vai_xxx..."}

# Create assistant
curl -X POST http://localhost:8000/api/assistants \
  -H 'X-API-Key: vai_xxx' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Support Bot","system_prompt":"You are a helpful support agent for Acme Inc."}'
# Returns: {"slug": "support-bot-a1b2c3", "share_url": "/talk/support-bot-a1b2c3"}

# Share the link!
# http://localhost:8000/talk/support-bot-a1b2c3
```

## Embed on Your Website

```html
<script src="http://localhost:8000/widget.js" data-assistant="support-bot-a1b2c3"></script>
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/tenants` | - | Create account |
| POST | `/api/assistants` | API Key | Create assistant |
| GET | `/api/assistants` | API Key | List assistants |
| GET | `/talk/{slug}` | Public | Voice chat page |
| POST | `/api/talk/{slug}/voice` | Public | Voice chat API |
| POST | `/api/talk/{slug}/text` | Public | Text chat API |
| GET | `/api/analytics/conversations` | API Key | List conversations |
| GET | `/api/analytics/stats` | API Key | Dashboard stats |

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy
- **Voice:** ElevenLabs (STT + TTS)
- **AI:** LiteLLM (100+ models) or OpenAI/DeepSeek direct
- **Database:** PostgreSQL (or SQLite for dev)
- **Deploy:** Docker, Railway, Render, VPS

## n8n Workflows Included

### 1. Voice Chat Pipeline (`n8n-workflow.json`)
Webhook receives audio → ElevenLabs STT → OpenAI/GPT response → ElevenLabs TTS → Returns audio + saves transcript to PostgreSQL → Optional webhook notification.

**Flow:** `Audio In → STT → LLM → TTS → Audio Out + DB Save`

### 2. Daily Conversation Digest (`n8n-daily-digest.json`)
Runs daily at 9 AM. Fetches 24h stats from database, gets recent conversations, generates AI summary, emails digest to owner.

**Import:** Open n8n → Settings → Import Workflow → paste JSON

**Required n8n credentials:**
- PostgreSQL connection
- SMTP (for email digest)
- Environment variables: `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_VOICE_ID`

## License

MIT — Use it however you want.
