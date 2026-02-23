from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def draft_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Одобрить", callback_data=f"approve:{post_id}")
    builder.button(text="Отклонить", callback_data=f"reject:{post_id}")
    builder.button(text="Редактировать", callback_data=f"edit:{post_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def approved_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Одобрено", callback_data=f"noop:{post_id}")
    builder.adjust(1)
    return builder.as_markup()


def rejected_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отклонено", callback_data=f"noop:{post_id}")
    builder.adjust(1)
    return builder.as_markup()


def published_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Опубликовано", callback_data=f"noop:{post_id}")
    builder.adjust(1)
    return builder.as_markup()
