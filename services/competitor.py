"""WF6: Monitor competitor Telegram channels via RSS, analyze via AI."""

import logging
import re
from datetime import datetime

import httpx

from database import save_competitor_insight
from prompts import COMPETITOR_ANALYSIS
from services.ai_client import ask_ai_json

logger = logging.getLogger(__name__)

# Competitor Telegram channels to monitor via RSSHub
COMPETITOR_CHANNELS = [
    "leaderteamuz",
    "pixie_uz",
    "telecom_uz",
]

RSSHUB_BASE = "https://rsshub.app/telegram/channel/{channel}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SMM-Agent/1.0)"}


async def run_competitor_monitoring() -> dict:
    """Full WF6: fetch competitor RSS → parse → AI analyze → save."""
    logger.info("WF6: Starting competitor monitoring")

    # 1. Fetch competitor posts
    all_posts = await _fetch_competitor_posts()
    if not all_posts:
        logger.warning("WF6: No competitor data fetched")
        return {"error": "No competitor data"}

    # 2. AI analysis
    posts_text = "\n---\n".join(
        f"{p['title']}" + (f": {p['description']}" if p.get("description") else "")
        for p in all_posts[:20]
    )
    prompt = COMPETITOR_ANALYSIS.format(count=len(all_posts), posts=posts_text)
    analysis = await ask_ai_json(
        prompt,
        system="Ты стратег по контент-маркетингу. Отвечай строго JSON без markdown.",
    )

    if not analysis:
        logger.error("WF6: AI analysis failed")
        return {"error": "AI analysis failed"}

    # 3. Save to DB
    today = datetime.now().strftime("%Y-%m-%d")
    await save_competitor_insight(today, analysis, posts_text)

    logger.info(f"WF6: Saved competitor insights for {today}")
    return {"date": today, "analysis": analysis, "posts_count": len(all_posts)}


async def _fetch_competitor_posts() -> list[dict]:
    """Fetch and parse RSS feeds from competitor channels."""
    posts = []

    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        for channel in COMPETITOR_CHANNELS:
            url = RSSHUB_BASE.format(channel=channel)
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                channel_posts = _parse_rss(resp.text, channel)
                posts.extend(channel_posts)
                logger.info(f"WF6: {channel} -> {len(channel_posts)} posts")
            except Exception as e:
                logger.warning(f"WF6: Failed to fetch {channel}: {e}")

    return posts


def _parse_rss(body: str, source: str) -> list[dict]:
    """Parse titles and descriptions from RSS XML."""
    # CDATA titles
    cdata = re.findall(r"<title><!\[CDATA\[([^\]]{10,200})\]\]>", body)
    plain = re.findall(r"<title>([^<]{10,150})</title>", body)
    plain = [t.strip() for t in plain if not t.startswith("http") and "<?" not in t]

    # Descriptions
    descs = re.findall(r"<description><!\[CDATA\[(.+?)\]\]></description>", body, re.DOTALL)
    descs = [re.sub(r"<[^>]+>", "", d).strip()[:200] for d in descs]

    titles = list(dict.fromkeys(cdata + plain))[:8]

    return [
        {"title": t, "description": descs[i] if i < len(descs) else "", "source": source}
        for i, t in enumerate(titles)
    ]
