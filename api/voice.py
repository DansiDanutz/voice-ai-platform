"""Voice processing: STT, TTS, and LLM pipeline."""
import os
import time
import httpx

ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")


async def speech_to_text(audio_bytes: bytes, mime: str = "audio/webm") -> dict:
    """Convert speech to text using ElevenLabs Scribe."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": ELEVENLABS_KEY},
            files={"file": ("audio.webm", audio_bytes, mime)},
            data={"model_id": "scribe_v1"},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"text": data.get("text", ""), "language": data.get("language", "en")}


async def text_to_speech(text: str, voice_id: str = "cjVigY5qzO86Huf0OWal") -> bytes:
    """Convert text to speech using ElevenLabs."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_KEY,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5,
                    "use_speaker_boost": True,
                },
            },
        )
        resp.raise_for_status()
        return resp.content


async def llm_respond(messages: list, model: str = "gpt-4o-mini") -> dict:
    """Get LLM response. Tries LiteLLM first, falls back to direct providers."""
    start = time.time()

    # Determine API details
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY", "")
    base_url = "https://api.openai.com/v1"
    if os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        base_url = "https://api.deepseek.com"
        model = "deepseek-chat"

    # Try LiteLLM first
    try:
        from litellm import acompletion
        resp = await acompletion(
            model=f"deepseek/{model}" if "deepseek" in base_url else model,
            messages=messages, max_tokens=300, temperature=0.7,
            api_key=api_key, api_base=base_url if "deepseek" in base_url else None,
        )
        text = resp.choices[0].message.content
        tokens = resp.usage.total_tokens if resp.usage else 0
        return {"text": text, "tokens": tokens, "latency_ms": int((time.time() - start) * 1000)}
    except Exception:
        pass

    # Fallback: direct HTTP
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 300, "temperature": 0.7},
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return {"text": text, "tokens": tokens, "latency_ms": int((time.time() - start) * 1000)}


async def voice_chat_pipeline(audio_bytes: bytes, system_prompt: str, voice_id: str, model: str = "gpt-4o-mini", history: list = None) -> dict:
    """Full pipeline: audio in → transcript → LLM → audio out."""
    # Step 1: STT
    stt_result = await speech_to_text(audio_bytes)
    transcript = stt_result["text"]
    if not transcript.strip():
        return {"error": "No speech detected", "transcript": ""}

    # Step 2: Build messages
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": transcript})

    # Step 3: LLM
    llm_result = await llm_respond(messages, model=model)

    # Step 4: TTS
    audio = await text_to_speech(llm_result["text"], voice_id=voice_id)

    return {
        "transcript": transcript,
        "response": llm_result["text"],
        "audio": audio,
        "tokens": llm_result["tokens"],
        "latency_ms": llm_result["latency_ms"],
        "language": stt_result["language"],
    }
