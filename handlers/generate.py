import logging
from io import BytesIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from config import ADMIN_CHAT_ID, BRANDS
from database import get_post, set_post_admin_message_id
from keyboards import draft_keyboard
from services.post_generator import run_post_generation
from utils import parse_project_platform, format_post_card, split_message

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("generate"))
async def cmd_generate(message: Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    args = message.text.replace("/generate", "").strip()
    project_id, platform = None, None
    if args:
        project_id, platform = parse_project_platform(args)
        if not project_id:
            await message.answer(
                "Не удалось определить проект.\n"
                "Пример: /generate личный тг\n"
                "Доступные: " + ", ".join(
                    f"{b['name']}" for b in BRANDS.values()
                )
            )
            return

    await message.answer("Генерирую посты + визуалы...")

    posts = await run_post_generation(project_id, platform)

    if not posts:
        await message.answer("Не удалось сгенерировать посты. Проверь логи.")
        return

    for post_data in posts:
        post = await get_post(post_data["id"])
        if not post:
            continue

        # Send image if generated
        image_data = post_data.get("image_data")
        if image_data:
            photo = BufferedInputFile(image_data, filename=f"post_{post['id']}.png")
            await message.answer_photo(photo, caption=f"Визуал для поста #{post['id']}")

        # Send text card with buttons
        card = format_post_card(post)
        for i, part in enumerate(split_message(card)):
            if i == 0:
                sent = await message.answer(
                    part,
                    reply_markup=draft_keyboard(post["id"]),
                )
                await set_post_admin_message_id(post["id"], sent.message_id)
            else:
                await message.answer(part)

    await message.answer(f"Готово! Сгенерировано {len(posts)} постов с визуалами.")
