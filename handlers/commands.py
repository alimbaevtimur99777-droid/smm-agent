import json
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_CHAT_ID, BRANDS
from database import (
    get_today_trends, get_posts_stats, get_drafts, get_latest_report,
    get_latest_competitor_insight,
)
from utils import format_trends_card, split_message, format_post_card

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_CHAT_ID


@router.message(Command("start"))
async def cmd_start(message: Message):
    if not _is_admin(message):
        return
    await message.answer(
        "<b>SMM Agent</b>\n\n"
        "Автономный SMM-агент для трёх брендов.\n"
        "Используй /help для списка команд."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not _is_admin(message):
        return
    await message.answer(
        "<b>Команды:</b>\n\n"
        "/generate [проект] [платформа] — генерация постов\n"
        "  Пример: /generate личный тг\n"
        "  Без аргументов — все проекты\n\n"
        "/trends — тренды сегодня\n"
        "/status — черновики и статистика\n"
        "/report — последний недельный отчёт\n"
        "/competitors — последний анализ конкурентов\n"
        "/brands — список брендов\n"
        "/help — эта справка"
    )


@router.message(Command("trends"))
async def cmd_trends(message: Message):
    if not _is_admin(message):
        return
    trends = await get_today_trends()
    text = format_trends_card(trends)
    await message.answer(text)


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not _is_admin(message):
        return
    stats = await get_posts_stats()
    drafts = await get_drafts()

    lines = [
        "<b>Статистика постов:</b>",
        f"  Черновики: {stats['draft']}",
        f"  Одобрены: {stats['approved']}",
        f"  Опубликованы: {stats['published']}",
        f"  Отклонены: {stats['rejected']}",
        f"  Всего: {stats['total']}",
    ]

    if drafts:
        lines.append("")
        lines.append(f"<b>Черновики ({len(drafts)}):</b>")
        for d in drafts[:5]:
            brand = BRANDS.get(d["project_id"], {})
            name = brand.get("name", d["project_id"])
            lines.append(f"  #{d['id']} {name} / {d['platform']}")

    await message.answer("\n".join(lines))


@router.message(Command("report"))
async def cmd_report(message: Message):
    if not _is_admin(message):
        return
    report = await get_latest_report()
    if not report:
        await message.answer("Отчётов пока нет.")
        return

    header = f"<b>Отчёт {report['week_start']} — {report['week_end']}</b>\n\n"
    for part in split_message(header + report["content"]):
        await message.answer(part)


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    if not _is_admin(message):
        return
    insight = await get_latest_competitor_insight()
    if not insight:
        await message.answer("Анализ конкурентов пока не проводился.")
        return

    lines = [f"<b>Конкуренты {insight['date']}</b>", ""]

    topics = json.loads(insight.get("hot_topics", "[]"))
    if topics:
        lines.append("<b>Горячие темы:</b>")
        for t in topics:
            lines.append(f"  - {t}")
        lines.append("")

    gaps = json.loads(insight.get("content_gaps", "[]"))
    if gaps:
        lines.append("<b>Их пробелы (наши возможности):</b>")
        for g in gaps:
            lines.append(f"  - {g}")
        lines.append("")

    opps = json.loads(insight.get("opportunities", "[]"))
    if opps:
        lines.append("<b>Идеи для нас:</b>")
        for o in opps:
            lines.append(f"  - {o}")

    alert = insight.get("urgent_alert", "")
    if alert:
        lines.append("")
        lines.append(f"<b>СРОЧНО:</b> {alert}")

    for part in split_message("\n".join(lines)):
        await message.answer(part)


@router.message(Command("brands"))
async def cmd_brands(message: Message):
    if not _is_admin(message):
        return
    lines = ["<b>Бренды:</b>", ""]
    for pid, brand in BRANDS.items():
        lines.append(f"<b>{brand['name']}</b> ({pid})")
        lines.append(f"  Платформы: {', '.join(brand['platforms'])}")
        lines.append(f"  Аудитория: {brand['audience']}")
        lines.append("")
    await message.answer("\n".join(lines))
