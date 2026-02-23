"""WF1: Generate posts using AI based on trends + knowledge base."""

import logging
from datetime import datetime

from config import BRANDS
from database import (
    get_today_trends, get_insights, get_recent_posts, create_post,
)
from prompts import (
    MASTER_SYSTEM, POST_GENERATION,
    STYLE_PERSONAL_BRAND, STYLE_LEADER_TEAM, STYLE_PIXIE,
)
from services.ai_client import ask_ai
from services.image_generator import generate_image

logger = logging.getLogger(__name__)

STYLE_MAP = {
    "personal_brand": STYLE_PERSONAL_BRAND,
    "leader_team": STYLE_LEADER_TEAM,
    "pixie": STYLE_PIXIE,
}


async def run_post_generation(project_id: str = None, platform: str = None) -> list[dict]:
    """Generate posts for specified or all projects/platforms.

    Returns list of created post dicts with id, project_id, platform, content, image_data.
    """
    logger.info("WF1: Starting post generation")
    today = datetime.now().strftime("%Y-%m-%d")
    created_posts = []

    if project_id and platform:
        tasks = [(project_id, platform)]
    elif project_id:
        brand = BRANDS.get(project_id, {})
        tasks = [(project_id, p) for p in brand.get("platforms", ["telegram"])]
    else:
        tasks = []
        for pid, brand in BRANDS.items():
            for p in brand.get("platforms", ["telegram"]):
                tasks.append((pid, p))

    trends = await get_today_trends(today)
    trends_by_project = {t["project_id"]: t for t in trends}

    for pid, plat in tasks:
        try:
            post = await _generate_single(pid, plat, trends_by_project)
            if post:
                created_posts.append(post)
        except Exception as e:
            logger.error(f"WF1: Error generating {pid}/{plat}: {e}")

    logger.info(f"WF1: Generated {len(created_posts)} posts")
    return created_posts


async def _generate_single(project_id: str, platform: str,
                           trends_by_project: dict) -> dict | None:
    """Generate a single post via AI + visual."""
    brand = BRANDS.get(project_id)
    if not brand:
        return None

    trend_data = trends_by_project.get(project_id, {})
    trend = trend_data.get("trend", "") if trend_data else ""
    idea = trend_data.get("idea", "") if trend_data else ""

    insights_list = await get_insights(project_id, limit=8)
    insights_text = "\n".join(
        f"[{i['type']}] {i['insight']}" for i in insights_list
    ) or "база знаний пока пуста"

    recent = await get_recent_posts(project_id, limit=5)
    recent_text = "\n".join(
        f"- {p['platform']}: {p['content'][:100]}..." for p in recent
    ) or "нет предыдущих постов"

    style_ref = STYLE_MAP.get(project_id, "")

    prompt = POST_GENERATION.format(
        platform=platform,
        project_name=brand["name"],
        voice=brand["voice"],
        audience=brand["audience"],
        goal=brand["goal"],
        topics=brand["topics"],
        forbidden=brand["forbidden"],
        trend=trend or "нет тренда — используй вечнозелёную тему",
        idea=idea,
        insights=insights_text,
        recent_posts=recent_text,
        style_reference=style_ref,
    )

    content = await ask_ai(prompt, system=MASTER_SYSTEM, max_tokens=2000)
    if not content or content == "AI unavailable":
        logger.error(f"WF1: AI failed for {project_id}/{platform}")
        return None

    # Generate visual
    image_data = await generate_image(content, brand["name"])

    post_id = await create_post(project_id, platform, content)
    logger.info(f"WF1: Created post #{post_id} for {project_id}/{platform}")

    return {
        "id": post_id,
        "project_id": project_id,
        "platform": platform,
        "content": content,
        "image_data": image_data,
    }
