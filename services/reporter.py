"""WF5: Weekly report — aggregate stats, AI analysis, update knowledge base."""

import json
import logging
from datetime import datetime, timedelta

from config import BRANDS
from database import (
    get_published_posts_for_week, get_insights, save_report, add_insight,
)
from prompts import WEEKLY_REPORT, KB_UPDATE
from services.ai_client import ask_ai, ask_ai_json

logger = logging.getLogger(__name__)


async def run_weekly_report() -> dict:
    """Full WF5: collect week stats, generate report, update KB."""
    logger.info("WF5: Starting weekly report")

    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")

    # 1. Get published posts
    posts = await get_published_posts_for_week()

    # 2. Group by project
    by_project = {}
    for p in posts:
        pid = p["project_id"]
        if pid not in by_project:
            brand = BRANDS.get(pid, {})
            by_project[pid] = {"name": brand.get("name", pid), "posts": [], "count": 0}
        by_project[pid]["posts"].append(p)
        by_project[pid]["count"] += 1

    stats_text = ""
    for pid, data in by_project.items():
        stats_text += f"\n{data['name']}: {data['count']} постов\n"
        for p in data["posts"]:
            stats_text += f"  - [{p['platform']}] {p['content'][:80]}...\n"

    # 3. Get current insights
    insights_list = await get_insights(limit=10)
    insights_text = "\n".join(
        f"[{i['type']}] {i['insight']}" for i in insights_list
    ) or "пусто"

    # 4. Generate report
    prompt = WEEKLY_REPORT.format(
        week_start=week_start,
        week_end=week_end,
        total_posts=len(posts),
        stats=stats_text or "Нет опубликованных постов за неделю.",
        insights=insights_text,
    )
    report_text = await ask_ai(prompt, system="Ты аналитик SMM. Пиши кратко, без воды.")

    # 5. Save report
    report_id = await save_report(week_start, week_end, report_text)

    # 6. Update knowledge base
    await _update_knowledge_base(posts, insights_text)

    logger.info(f"WF5: Report #{report_id} saved")
    return {
        "report_id": report_id,
        "report_text": report_text,
        "total_posts": len(posts),
        "week_start": week_start,
        "week_end": week_end,
    }


async def _update_knowledge_base(posts: list[dict], current_knowledge: str):
    """Ask AI to analyze posts and generate new insights for KB."""
    if not posts:
        return

    posts_text = "\n".join(
        f"[{p['project_id']}] [{p['platform']}] {p['content'][:150]}..."
        for p in posts
    )

    prompt = KB_UPDATE.format(posts=posts_text, current_knowledge=current_knowledge)
    result = await ask_ai_json(
        prompt,
        system="Ты аналитик SMM. Отвечай строго JSON.",
    )

    new_insights = result.get("new_insights", [])
    for ins in new_insights:
        await add_insight(
            project_id=ins.get("project", ""),
            insight_type=ins.get("type", "content_insight"),
            insight=ins.get("insight", ""),
            evidence=ins.get("evidence", ""),
        )
    logger.info(f"WF5: Added {len(new_insights)} new insights to KB")
