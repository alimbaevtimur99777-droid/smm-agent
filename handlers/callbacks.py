import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_CHAT_ID
from database import get_post, update_post_status, update_post_content
from keyboards import approved_keyboard, rejected_keyboard, draft_keyboard
from utils import format_post_card

router = Router()
logger = logging.getLogger(__name__)


class EditPost(StatesGroup):
    waiting_for_text = State()


@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("Только админ.", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    post = await get_post(post_id)
    if not post:
        await callback.answer("Пост не найден.", show_alert=True)
        return

    if post["status"] != "draft":
        await callback.answer(f"Пост уже {post['status']}.", show_alert=True)
        return

    await update_post_status(post_id, "approved")
    post = await get_post(post_id)
    card = format_post_card(post)

    try:
        await callback.message.edit_text(
            text=card,
            reply_markup=approved_keyboard(post_id),
        )
    except Exception:
        pass

    await callback.answer("Одобрено! Будет опубликован по расписанию.")
    logger.info(f"Post #{post_id} approved")


@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("Только админ.", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    post = await get_post(post_id)
    if not post:
        await callback.answer("Пост не найден.", show_alert=True)
        return

    await update_post_status(post_id, "rejected")
    post = await get_post(post_id)
    card = format_post_card(post)

    try:
        await callback.message.edit_text(
            text=card,
            reply_markup=rejected_keyboard(post_id),
        )
    except Exception:
        pass

    await callback.answer("Отклонено.")
    logger.info(f"Post #{post_id} rejected")


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("Только админ.", show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])
    post = await get_post(post_id)
    if not post:
        await callback.answer("Пост не найден.", show_alert=True)
        return

    await state.set_state(EditPost.waiting_for_text)
    await state.update_data(edit_post_id=post_id, edit_message_id=callback.message.message_id)
    await callback.message.answer(
        f"Отправьте новый текст для поста #{post_id}.\n"
        "Или /cancel для отмены."
    )
    await callback.answer()


@router.message(EditPost.waiting_for_text, F.text)
async def process_edit(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_CHAT_ID:
        return

    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Редактирование отменено.")
        return

    data = await state.get_data()
    post_id = data["edit_post_id"]
    edit_msg_id = data.get("edit_message_id")

    await update_post_content(post_id, message.text)
    post = await get_post(post_id)
    card = format_post_card(post)

    # Update the original draft message
    if edit_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=ADMIN_CHAT_ID,
                message_id=edit_msg_id,
                text=card,
                reply_markup=draft_keyboard(post_id),
            )
        except Exception:
            pass

    await state.clear()
    await message.answer(f"Пост #{post_id} обновлён.")
    logger.info(f"Post #{post_id} edited")


@router.callback_query(F.data.startswith("noop:"))
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
