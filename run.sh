#!/bin/bash
export PATH="/home/Memo1981/.local/bin:$PATH"
cd /home/Memo1981/n8n-automations/voice-ai-platform
set -a; source .env; set +a
exec uvicorn main:app --host 0.0.0.0 --port 8500
