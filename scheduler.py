"""APScheduler cron job registration for all workflows."""

import logging
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ADMIN_CHAT_ID, BRANDS, TIMEZONE
from utils import split_message, format_post_card, format_trends_card

logger = logging.getLogger(__name__)


def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot):
    """Register all cron jobs."""

    # WF6: Competitor monitoring — 06:00 daily
    scheduler.add_job(
        _job_competitors,
        CronTrigger(hour=6, minute=0, timezone=TIMEZONE),
        id="wf6_competitors",
        kwargs={"bot": bot},
        replace_existing=True,
    )

    # WF2: Trend monitoring — 07:00 daily
    scheduler.add_job(
        _job_trends,
        CronTrigger(hour=7, minute=0, timezone=TIMEZONE),
        id="wf2_trends",
        kwargs={"bot": bot},
        replace_existing=True,
    )

    # WF1: Post generation — 08:00 daily
    scheduler.add_job(
        _job_generate,
        CronTrigger(hour=8, minute=0, timezone=TIMEZONE),
        id="wf1_generate",
        kwargs={"bot": bot},
        replace_existing=True,
    )

    # WF4: Auto-publish — 10:00, 14:00, 18:00 daily
    scheduler.add_job(
        _job_publish,
        CronTrigger(hour="10,14,18", minute=0, timezone=TIMEZONE),
        id="wf4_publish",
        kwargs={"bot": bot},
        replace_existing=True,
    )

    # WF5: Weekly report — Monday 09:00
    scheduler.add_job(
        _job_report,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=TIMEZONE),
        id="wf5_report",
        kwargs={"bot": bot},
        replace_existing=True,
    )

    logger.info("Scheduler: all cron jobs registered")


async def _job_competitors(bot: Bot):
    """WF6: Run competitor monitoring and notify admin."""
    try:
        from services.competitor import run_competitor_monitoring
        import json

        result = await run_competitor_monitoring()
        analysis = result.get("analysis", {})

        if result.get("error"):
            await bot.send_message(ADMIN_CHAT_ID, f"WF6: {result['error']}")
            return

        lines = [f"<b>Конкуренты {result['date']}</b>", ""]
        topics = analysis.get("hot_topics", [])
        if topics:
            lines.append("<b>Горячие темы:</b>")
            for t in topics:
                lines.append(f"  - {t}")
            lines.append("")

        gaps = analysis.get("content_gaps", [])
        if gaps:
            lines.append("<b>Пробелы (наши возможности):</b>")
            for g in gaps:
                lines.append(f"  - {g}")
            lines.append("")

        opps = analysis.get("our_opportunities", [])
        if opps:
            lines.append("<b>Идеи для нас:</b>")
            for o in opps:
                lines.append(f"  - {o}")

        alert = analysis.get("urgent_alert", "")
        if alert:
            lines.append(f"\n<b>СРОЧНО:</b> {alert}")

        for part in split_message("\n".join(lines)):
            await bot.send_message(ADMIN_CHAT_ID, part)

    except Exception as e:
        logger.error(f"WF6 job error: {e}")
        await bot.send_message(ADMIN_CHAT_ID, f"WF6 error: {e}")


async def _job_trends(bot: Bot):
    """WF2: Run trend monitoring and notify admin."""
    try:
        from services.trend_monitor import run_trend_monitoring
        from database import get_today_trends

        result = await run_trend_monitoring()

        if result.get("error"):
            await bot.send_message(ADMIN_CHAT_ID, f"WF2: {result['error']}")
            return

        trends = await get_today_trends()
        text = format_trends_card(trends)
        for part in split_message(text):
            await bot.send_message(ADMIN_CHAT_ID, part)

    except Exception as e:
        logger.error(f"WF2 job error: {e}")
        await bot.send_message(ADMIN_CHAT_ID, f"WF2 error: {e}")


async def _job_generate(bot: Bot):
    """WF1: Generate posts and send drafts for approval."""
    try:
        from services.post_generator import run_post_generation
        from database import get_post, set_post_admin_message_id
        from keyboards import draft_keyboard

        posts = await run_post_generation()

        if not posts:
            await bot.send_message(ADMIN_CHAT_ID, "WF1: Не удалось сгенерировать посты.")
            return

        for post_data in posts:
            post = await get_post(post_data["id"])
            if not post:
                continue
            card = format_post_card(post)
            parts = split_message(card)
            for i, part in enumerate(parts):
                if i == 0:
                    sent = await bot.send_message(
                        ADMIN_CHAT_ID, part,
                        reply_markup=draft_keyboard(post["id"]),
                    )
                    await set_post_admin_message_id(post["id"], sent.message_id)
                else:
                    await bot.send_message(ADMIN_CHAT_ID, part)

        await bot.send_message(
            ADMIN_CHAT_ID,
            f"WF1: Сгенерировано {len(posts)} постов. Одобри или отклони выше."
        )

    except Exception as e:
        logger.error(f"WF1 job error: {e}")
        await bot.send_message(ADMIN_CHAT_ID, f"WF1 error: {e}")


async def _job_publish(bot: Bot):
    """WF4: Publish approved posts to channel."""
    try:
        from services.publisher import run_publisher

        published = await run_publisher(bot)

        if published:
            names = ", ".join(
                f"#{p['id']}" for p in published
            )
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"WF4: Опубликовано {len(published)} постов: {names}"
            )

    except Exception as e:
        logger.error(f"WF4 job error: {e}")
        await bot.send_message(ADMIN_CHAT_ID, f"WF4 error: {e}")


async def _job_report(bot: Bot):
    """WF5: Weekly report."""
    try:
        from services.reporter import run_weekly_report

        result = await run_weekly_report()
        report_text = result.get("report_text", "No report generated")

        header = (
            f"<b>Недельный отчёт {result['week_start']} — {result['week_end']}</b>\n"
            f"Постов за неделю: {result['total_posts']}\n\n"
        )
        for part in split_message(header + report_text):
            await bot.send_message(ADMIN_CHAT_ID, part)

    except Exception as e:
        logger.error(f"WF5 job error: {e}")
        await bot.send_message(ADMIN_CHAT_ID, f"WF5 error: {e}")
