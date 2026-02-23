import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, BRANDS, ADMIN_CHAT_ID
from database import init_db, upsert_project
from handlers import commands, generate, callbacks
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    # 1. Init database
    await init_db()

    # 2. Seed brands
    for project_id, data in BRANDS.items():
        await upsert_project(project_id, data)

    # 3. Create bot
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 4. Register handlers
    dp.include_router(commands.router)
    dp.include_router(generate.router)
    dp.include_router(callbacks.router)

    # 5. Setup scheduler
    scheduler = AsyncIOScheduler()
    setup_scheduler(scheduler, bot)
    scheduler.start()

    # 6. Notify admin
    await bot.send_message(
        ADMIN_CHAT_ID,
        "<b>SMM Agent started</b>\n\n"
        "Расписание:\n"
        "  06:00 — мониторинг конкурентов\n"
        "  07:00 — сбор трендов\n"
        "  08:00 — генерация постов\n"
        "  10:00, 14:00, 18:00 — публикация\n"
        "  Пн 09:00 — недельный отчёт\n\n"
        "/help — команды",
    )

    # 7. Start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started (polling)")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
