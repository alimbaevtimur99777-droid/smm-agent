"""WF2: Collect trends from Google Trends + vc.ru, analyze via AI, save to DB."""

import logging
import re
from datetime import datetime

import httpx

from config import BRANDS
from database import save_trend, get_today_trends
from prompts import TREND_ANALYSIS
from services.ai_client import ask_ai_json

logger = logging.getLogger(__name__)

SOURCES = [
    ("Google Trends UZ", "https://trends.google.com/trends/trendingsearches/daily/rss?geo=UZ"),
    ("Google Trends RU", "https://trends.google.com/trends/trendingsearches/daily/rss?geo=RU"),
    ("vc.ru RSS", "https://vc.ru/rss"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SMM-Agent/1.0)"}


async def run_trend_monitoring() -> dict:
    """Full WF2 pipeline: fetch → parse → AI analyze → save."""
    logger.info("WF2: Starting trend monitoring")

    # 1. Fetch all RSS sources
    raw_trends = await _fetch_all_trends()
    if not raw_trends:
        logger.warning("WF2: No trends fetched")
        return {"error": "No trends fetched"}

    # 2. Ask AI to analyze trends for each project
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = TREND_ANALYSIS.format(
        count=len(raw_trends),
        trends="\n".join(raw_trends[:25]),
    )
    analysis = await ask_ai_json(
        prompt,
        system="Ты аналитик трендов. Отвечай строго JSON без markdown.",
    )

    if not analysis:
        logger.error("WF2: AI returned empty analysis")
        return {"error": "AI analysis failed"}

    # 3. Save trends for each project
    raw_str = "\n".join(raw_trends[:25])
    for project_id in BRANDS:
        proj_data = analysis.get(project_id, {})
        await save_trend(
            date=today,
            project_id=project_id,
            trend=proj_data.get("trend", ""),
            idea=proj_data.get("idea", ""),
            category=proj_data.get("category", ""),
            raw_trends=raw_str,
        )

    logger.info(f"WF2: Saved trends for {len(BRANDS)} projects")
    return {"date": today, "analysis": analysis, "raw_count": len(raw_trends)}


async def _fetch_all_trends() -> list[str]:
    """Fetch and parse trends from all RSS sources."""
    all_trends: set[str] = set()

    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        for name, url in SOURCES:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                titles = _parse_rss_titles(resp.text)
                all_trends.update(titles)
                logger.info(f"WF2: {name} -> {len(titles)} titles")
            except Exception as e:
                logger.warning(f"WF2: Failed to fetch {name}: {e}")

    return [t for t in all_trends if len(t) > 3]


def _parse_rss_titles(body: str) -> list[str]:
    """Extract titles from RSS XML body."""
    # CDATA titles (Google Trends format)
    cdata = re.findall(r"<title><!\[CDATA\[([^\]]+)\]\]></title>", body)
    # Plain titles (standard RSS)
    plain = re.findall(r"<title>([^<]{5,100})</title>", body)
    plain = [t.strip() for t in plain if "http" not in t and "<?" not in t]

    titles = list(dict.fromkeys(cdata + plain[:15]))  # deduplicate, preserve order
    return titles
