"""WF4: Publish approved posts to the Telegram channel."""

import logging

from aiogram import Bot

from config import CHANNEL_ID
from database import get_approved_posts, update_post_status, set_post_channel_message_id

logger = logging.getLogger(__name__)


async def run_publisher(bot: Bot) -> list[dict]:
    """Publish all approved posts scheduled for today."""
    logger.info("WF4: Starting publisher")
    posts = await get_approved_posts()

    if not posts:
        logger.info("WF4: No approved posts to publish")
        return []

    published = []
    for post in posts:
        try:
            msg = await bot.send_message(
                chat_id=CHANNEL_ID,
                text=post["content"],
            )
            await update_post_status(post["id"], "published")
            await set_post_channel_message_id(post["id"], msg.message_id)
            published.append(post)
            logger.info(f"WF4: Published post #{post['id']} to channel")
        except Exception as e:
            logger.error(f"WF4: Failed to publish post #{post['id']}: {e}")
            await update_post_status(post["id"], "error")

    logger.info(f"WF4: Published {len(published)}/{len(posts)} posts")
    return published
