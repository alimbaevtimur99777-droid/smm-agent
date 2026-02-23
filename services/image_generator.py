"""Generate visuals for posts using Pollinations.ai (free, no API key)."""

import logging
import urllib.parse

import httpx

from services.ai_client import ask_ai

logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1080&nologo=true"


async def generate_visual_prompt(post_content: str, brand_name: str) -> str:
    """Ask AI to create an image generation prompt based on post content."""
    prompt = f"""Создай промпт для генерации изображения к посту в соцсетях.

Бренд: {brand_name}
Текст поста (фрагмент): {post_content[:300]}

Требования к промпту:
- На АНГЛИЙСКОМ языке (для генератора изображений)
- Описание визуала: минималистичный, современный, бизнес-стиль
- НЕ включай текст/надписи в изображение
- Абстрактный или тематический визуал
- Корпоративные цвета, чистый фон
- Стиль: flat design или 3D render

Верни ТОЛЬКО промпт для генерации (1-2 предложения на английском)."""

    result = await ask_ai(prompt, max_tokens=150)
    if not result or result == "AI unavailable":
        return f"Modern minimalist business illustration for {brand_name}, clean corporate style, blue tones"
    return result.strip().strip('"').strip("'")


async def generate_image(post_content: str, brand_name: str) -> bytes | None:
    """Generate an image for a post. Returns image bytes or None."""
    try:
        img_prompt = await generate_visual_prompt(post_content, brand_name)
        encoded = urllib.parse.quote(img_prompt)
        url = POLLINATIONS_URL.format(prompt=encoded)

        logger.info(f"Generating image: {img_prompt[:80]}...")
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("image"):
                logger.info(f"Image generated: {len(resp.content)} bytes")
                return resp.content

        logger.warning("Response is not an image")
        return None
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None
