# Build History: Voice AI Platform

## Step 1: Architecture Design
Designed multi-tenant voice AI platform with FastAPI backend. Key models: Tenant → Assistant → Conversation → Message. Each tenant gets an API key, creates assistants with custom voices/personalities, shares public links.

## Step 2: Voice Pipeline (STT → LLM → TTS)
Built `api/voice.py` with 4 core functions:
- `speech_to_text()` — ElevenLabs Scribe API
- `text_to_speech()` — ElevenLabs multilingual v2
- `llm_respond()` — LiteLLM (100+ models) with direct fallback
- `voice_chat_pipeline()` — Orchestrates all 3 in sequence

## Step 3: Database Models
SQLAlchemy models with PostgreSQL/SQLite support:
- `Tenant` — Multi-tenant accounts with API keys and Stripe IDs
- `Assistant` — Custom AI assistants with voice, personality, knowledge base
- `Conversation` — Session tracking with sentiment and summaries
- `Message` — Individual messages with latency and token tracking

## Step 4: Public Voice Chat Page
Built inline HTML page served at `/talk/{slug}`. Features:
- Microphone recording with MediaRecorder API
- Real-time status indicators (idle/recording/processing)
- Conversation history display
- Auto-play AI audio responses
- Mobile-responsive dark theme

## Step 5: REST API
17 endpoints total:
- Tenant management (create account, get API key)
- Assistant CRUD (create, list, update, delete)
- Public voice/text chat (no auth required)
- Analytics (conversations, messages, stats)
- Embeddable widget.js

## Step 6: Widget System
Created `/widget.js` — a single script tag that adds a floating microphone button to any website. Click opens the voice chat in a popup window. Zero configuration needed.

## Step 7: Docker + Production Setup
- `Dockerfile` for single container deployment
- `docker-compose.yml` with PostgreSQL
- `setup.sh` for quick local development
- Environment-based configuration
