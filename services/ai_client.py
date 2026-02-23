import json
import logging
import re

import httpx

from config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


async def ask_ai(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    """Groq (primary) -> Gemini (fallback)."""
    result = await _ask_groq(prompt, system, max_tokens)
    if result and not result.startswith("ERR:"):
        return result

    logger.warning("Groq failed, trying Gemini fallback...")
    result = await _ask_gemini(prompt, system, max_tokens)
    if result and not result.startswith("ERR:"):
        return result

    return "AI unavailable"


async def ask_ai_json(prompt: str, system: str = "", max_tokens: int = 2048) -> dict:
    """Ask AI and parse JSON response."""
    raw = await ask_ai(prompt, system, max_tokens)
    return _extract_json(raw)


async def _ask_groq(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"ERR: {e}"


async def _ask_gemini(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    url = GEMINI_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)
    body = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"ERR: {e}"


def _extract_json(text: str) -> dict:
    """Extract JSON from AI response that may contain markdown fences."""
    # Remove markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning(f"Failed to parse JSON from AI response: {text[:200]}")
    return {}
