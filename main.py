"""Voice AI Platform — Main API server."""
import os
import uuid
import base64
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from api.database import init_db, get_db
from api.models import Tenant, Assistant, Conversation, Message
from api.voice import voice_chat_pipeline, text_to_speech, llm_respond, speech_to_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Voice AI Platform",
    description="Complete voice AI assistant platform. Share a link, users talk to your AI, transcripts saved automatically.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ──────────────────────────────────────────────

class AssistantCreate(BaseModel):
    name: str
    system_prompt: str = "You are a helpful AI voice assistant. Keep responses concise (1-3 sentences) for natural conversation."
    voice_id: str = "cjVigY5qzO86Huf0OWal"
    voice_name: str = "Eric"
    model: str = "gpt-4o-mini"
    language: str = "en"
    greeting: str = "Hello! How can I help you today?"
    knowledge_base: Optional[str] = None

class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_id: Optional[str] = None
    model: Optional[str] = None
    greeting: Optional[str] = None
    knowledge_base: Optional[str] = None
    is_active: Optional[bool] = None

class TextChatRequest(BaseModel):
    message: str
    visitor_id: Optional[str] = None
    conversation_id: Optional[str] = None

class TenantCreate(BaseModel):
    name: str
    email: str


# ── Auth helpers ─────────────────────────────────────────

def get_tenant_by_api_key(request: Request, db: Session = Depends(get_db)) -> Tenant:
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        raise HTTPException(401, "Missing X-API-Key header")
    tenant = db.query(Tenant).filter(Tenant.api_key == api_key).first()
    if not tenant:
        raise HTTPException(401, "Invalid API key")
    return tenant


# ── Health ───────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "voice-ai-platform", "version": "1.0.0"}


# ── Tenant Management ───────────────────────────────────

@app.post("/api/tenants")
def create_tenant(data: TenantCreate, db: Session = Depends(get_db)):
    api_key = f"vai_{uuid.uuid4().hex[:32]}"
    tenant = Tenant(name=data.name, email=data.email, api_key=api_key)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": str(tenant.id), "name": tenant.name, "api_key": api_key, "plan": tenant.plan}


# ── Assistant CRUD ───────────────────────────────────────

@app.post("/api/assistants")
def create_assistant(data: AssistantCreate, tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    slug = f"{data.name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    assistant = Assistant(
        tenant_id=tenant.id, name=data.name, slug=slug,
        system_prompt=data.system_prompt, voice_id=data.voice_id,
        voice_name=data.voice_name, model=data.model,
        language=data.language, greeting=data.greeting,
        knowledge_base=data.knowledge_base,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return {
        "id": str(assistant.id), "name": assistant.name, "slug": assistant.slug,
        "share_url": f"/talk/{assistant.slug}",
        "widget_code": f'<script src="/widget.js" data-assistant="{assistant.slug}"></script>',
    }

@app.get("/api/assistants")
def list_assistants(tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    assistants = db.query(Assistant).filter(Assistant.tenant_id == tenant.id).all()
    return [{"id": str(a.id), "name": a.name, "slug": a.slug, "voice_name": a.voice_name,
             "model": a.model, "is_active": a.is_active,
             "conversations": len(a.conversations)} for a in assistants]

@app.patch("/api/assistants/{assistant_id}")
def update_assistant(assistant_id: str, data: AssistantUpdate, tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id, Assistant.tenant_id == tenant.id).first()
    if not assistant:
        raise HTTPException(404, "Assistant not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(assistant, k, v)
    db.commit()
    return {"status": "updated"}

@app.delete("/api/assistants/{assistant_id}")
def delete_assistant(assistant_id: str, tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id, Assistant.tenant_id == tenant.id).first()
    if not assistant:
        raise HTTPException(404, "Assistant not found")
    db.delete(assistant)
    db.commit()
    return {"status": "deleted"}


# ── Public Voice Chat (shareable link) ──────────────────

@app.get("/talk/{slug}", response_class=HTMLResponse)
def talk_page(slug: str, db: Session = Depends(get_db)):
    assistant = db.query(Assistant).filter(Assistant.slug == slug, Assistant.is_active == True).first()
    if not assistant:
        raise HTTPException(404, "Assistant not found or inactive")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Talk to {assistant.name}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.container {{ max-width:480px; width:100%; padding:2rem; text-align:center; }}
h1 {{ font-size:1.5rem; margin-bottom:0.5rem; }}
.subtitle {{ color:#94a3b8; margin-bottom:2rem; }}
.mic-btn {{ width:120px; height:120px; border-radius:50%; border:none; cursor:pointer; font-size:2rem; transition:all 0.3s; }}
.mic-btn.idle {{ background:linear-gradient(135deg,#3b82f6,#8b5cf6); color:white; box-shadow:0 0 30px rgba(59,130,246,0.3); }}
.mic-btn.recording {{ background:linear-gradient(135deg,#ef4444,#f97316); color:white; box-shadow:0 0 30px rgba(239,68,68,0.5); animation:pulse 1s infinite; }}
.mic-btn.processing {{ background:#374151; color:#9ca3af; cursor:wait; }}
@keyframes pulse {{ 0%,100% {{ transform:scale(1); }} 50% {{ transform:scale(1.05); }} }}
.status {{ margin-top:1rem; color:#94a3b8; font-size:0.9rem; }}
.messages {{ margin-top:2rem; text-align:left; max-height:400px; overflow-y:auto; }}
.msg {{ padding:0.75rem 1rem; margin:0.5rem 0; border-radius:12px; font-size:0.9rem; max-width:85%; }}
.msg.user {{ background:#1e3a5f; margin-left:auto; }}
.msg.ai {{ background:#1e293b; border:1px solid #334155; }}
.msg .role {{ font-size:0.7rem; color:#64748b; margin-bottom:0.25rem; }}
.greeting {{ background:#1e293b; border:1px solid #334155; padding:1rem; border-radius:12px; margin-bottom:1.5rem; }}
</style></head><body>
<div class="container">
  <h1>🎙️ {assistant.name}</h1>
  <p class="subtitle">Tap to talk</p>
  <div class="greeting">{assistant.greeting}</div>
  <button class="mic-btn idle" id="mic" onclick="toggleRecording()">🎤</button>
  <div class="status" id="status">Tap the microphone to start</div>
  <div class="messages" id="messages"></div>
</div>
<script>
const SLUG = "{assistant.slug}";
let recording = false, mediaRecorder = null, chunks = [], convId = null;
const mic = document.getElementById('mic'), status = document.getElementById('status'), msgs = document.getElementById('messages');

function addMsg(text, role) {{
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  d.innerHTML = '<div class="role">' + (role==='user'?'You':'{assistant.name}') + '</div>' + text;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}}

async function toggleRecording() {{
  if (recording) {{ mediaRecorder.stop(); return; }}
  try {{
    const stream = await navigator.mediaDevices.getUserMedia({{audio:{{echoCancellation:true,noiseSuppression:true}}}});
    mediaRecorder = new MediaRecorder(stream, {{mimeType:'audio/webm;codecs=opus'}});
    chunks = [];
    mediaRecorder.ondataavailable = e => {{ if(e.data.size>0) chunks.push(e.data); }};
    mediaRecorder.onstop = async () => {{
      stream.getTracks().forEach(t=>t.stop());
      recording = false;
      mic.className = 'mic-btn processing';
      mic.textContent = '⏳';
      status.textContent = 'Processing...';
      const blob = new Blob(chunks, {{type:'audio/webm'}});
      const form = new FormData();
      form.append('audio', blob);
      if(convId) form.append('conversation_id', convId);
      try {{
        const r = await fetch('/api/talk/' + SLUG + '/voice', {{method:'POST', body:form}});
        const data = await r.json();
        if(data.error) {{ status.textContent = data.error; }}
        else {{
          convId = data.conversation_id;
          addMsg(data.transcript, 'user');
          addMsg(data.response, 'ai');
          if(data.audio) {{
            const audio = new Audio('data:audio/mpeg;base64,' + data.audio);
            audio.play();
          }}
          status.textContent = 'Tap to talk again';
        }}
      }} catch(e) {{ status.textContent = 'Error: ' + e.message; }}
      mic.className = 'mic-btn idle';
      mic.textContent = '🎤';
    }};
    mediaRecorder.start();
    recording = true;
    mic.className = 'mic-btn recording';
    mic.textContent = '⏹️';
    status.textContent = 'Listening...';
  }} catch(e) {{ status.textContent = 'Microphone access denied'; }}
}}
</script></body></html>"""


@app.post("/api/talk/{slug}/voice")
async def voice_chat(slug: str, audio: UploadFile = File(...), conversation_id: Optional[str] = Form(None), db: Session = Depends(get_db)):
    """Public endpoint: voice in → transcript + AI response + audio out."""
    assistant = db.query(Assistant).filter(Assistant.slug == slug, Assistant.is_active == True).first()
    if not assistant:
        raise HTTPException(404, "Assistant not found")

    audio_bytes = await audio.read()

    # Build system prompt with knowledge base
    system = assistant.system_prompt
    if assistant.knowledge_base:
        system += f"\n\nKnowledge Base:\n{assistant.knowledge_base}"

    # Get conversation history
    history = []
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            for msg in db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).limit(20).all():
                history.append({"role": msg.role, "content": msg.text})

    # Run pipeline
    result = await voice_chat_pipeline(audio_bytes, system, assistant.voice_id, assistant.model, history)
    if result.get("error"):
        return JSONResponse({"error": result["error"]}, status_code=400)

    # Create/update conversation
    if not conv:
        conv = Conversation(assistant_id=assistant.id)
        db.add(conv)
        db.flush()

    # Save messages
    user_msg = Message(conversation_id=conv.id, role="user", text=result["transcript"])
    ai_msg = Message(conversation_id=conv.id, role="assistant", text=result["response"],
                     tokens_used=result["tokens"], latency_ms=result["latency_ms"])
    db.add_all([user_msg, ai_msg])
    conv.message_count = (conv.message_count or 0) + 2
    db.commit()

    # Encode audio as base64
    audio_b64 = base64.b64encode(result["audio"]).decode() if result.get("audio") else None

    return {
        "transcript": result["transcript"],
        "response": result["response"],
        "audio": audio_b64,
        "conversation_id": str(conv.id),
        "latency_ms": result["latency_ms"],
    }


@app.post("/api/talk/{slug}/text")
async def text_chat(slug: str, data: TextChatRequest, db: Session = Depends(get_db)):
    """Public endpoint: text in → AI response (+ optional TTS)."""
    assistant = db.query(Assistant).filter(Assistant.slug == slug, Assistant.is_active == True).first()
    if not assistant:
        raise HTTPException(404, "Assistant not found")

    system = assistant.system_prompt
    if assistant.knowledge_base:
        system += f"\n\nKnowledge Base:\n{assistant.knowledge_base}"

    # History
    history = []
    conv = None
    if data.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == data.conversation_id).first()
        if conv:
            for msg in db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).limit(20).all():
                history.append({"role": msg.role, "content": msg.text})

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": data.message}]
    result = await llm_respond(messages, model=assistant.model)

    if not conv:
        conv = Conversation(assistant_id=assistant.id, visitor_id=data.visitor_id)
        db.add(conv)
        db.flush()

    user_msg = Message(conversation_id=conv.id, role="user", text=data.message)
    ai_msg = Message(conversation_id=conv.id, role="assistant", text=result["text"],
                     tokens_used=result["tokens"], latency_ms=result["latency_ms"])
    db.add_all([user_msg, ai_msg])
    conv.message_count = (conv.message_count or 0) + 2
    db.commit()

    return {
        "response": result["text"],
        "conversation_id": str(conv.id),
        "tokens": result["tokens"],
        "latency_ms": result["latency_ms"],
    }


# ── Analytics (authenticated) ───────────────────────────

@app.get("/api/analytics/conversations")
def get_conversations(tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    assistants = db.query(Assistant).filter(Assistant.tenant_id == tenant.id).all()
    aid_list = [a.id for a in assistants]
    convs = db.query(Conversation).filter(Conversation.assistant_id.in_(aid_list)).order_by(Conversation.started_at.desc()).limit(100).all()
    return [{
        "id": str(c.id),
        "assistant": next((a.name for a in assistants if a.id == c.assistant_id), ""),
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "message_count": c.message_count,
        "duration_seconds": c.duration_seconds,
        "sentiment_score": c.sentiment_score,
        "summary": c.summary,
    } for c in convs]

@app.get("/api/analytics/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str, tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    # Verify tenant owns this
    assistant = db.query(Assistant).filter(Assistant.id == conv.assistant_id, Assistant.tenant_id == tenant.id).first()
    if not assistant:
        raise HTTPException(403, "Access denied")
    messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at).all()
    return [{"role": m.role, "text": m.text, "created_at": m.created_at.isoformat(), "latency_ms": m.latency_ms} for m in messages]

@app.get("/api/analytics/stats")
def get_stats(tenant: Tenant = Depends(get_tenant_by_api_key), db: Session = Depends(get_db)):
    assistants = db.query(Assistant).filter(Assistant.tenant_id == tenant.id).all()
    aid_list = [a.id for a in assistants]
    total_convs = db.query(Conversation).filter(Conversation.assistant_id.in_(aid_list)).count()
    total_msgs = db.query(Message).join(Conversation).filter(Conversation.assistant_id.in_(aid_list)).count()
    return {
        "total_assistants": len(assistants),
        "total_conversations": total_convs,
        "total_messages": total_msgs,
    }


# ── Widget JS ────────────────────────────────────────────

@app.get("/widget.js")
def widget_js():
    return HTMLResponse(content="""
(function(){
  var slug = document.currentScript.getAttribute('data-assistant');
  if(!slug) return;
  var btn = document.createElement('div');
  btn.innerHTML = '🎙️';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:white;display:flex;align-items:center;justify-content:center;font-size:24px;cursor:pointer;box-shadow:0 4px 20px rgba(59,130,246,0.4);z-index:9999;';
  btn.onclick = function(){ window.open('/talk/' + slug, '_blank', 'width=480,height=700'); };
  document.body.appendChild(btn);
})();
""", media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
