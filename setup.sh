#!/bin/bash
set -e

echo "🎙️ Voice AI Platform — Setup"
echo "=============================="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 required. Install it first."
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Setup env
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
    echo "   - ELEVENLABS_API_KEY (required for voice)"
    echo "   - OPENAI_API_KEY or DEEPSEEK_API_KEY (required for AI)"
    echo "   - DATABASE_URL (optional, defaults to SQLite)"
    echo ""
fi

# Init database
echo "🗄️ Initializing database..."
python3 -c "from api.database import init_db; init_db()"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Start the server:"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "📋 Then:"
echo "   1. Create a tenant:  curl -X POST http://localhost:8000/api/tenants -H 'Content-Type: application/json' -d '{\"name\":\"My Company\",\"email\":\"me@example.com\"}'"
echo "   2. Create assistant: curl -X POST http://localhost:8000/api/assistants -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' -d '{\"name\":\"Support Bot\"}'"
echo "   3. Share the link:   http://localhost:8000/talk/YOUR_SLUG"
echo ""
echo "📖 Full docs: http://localhost:8000/docs"
