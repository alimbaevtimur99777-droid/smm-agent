from config import BRANDS, BRAND_ALIASES, PLATFORM_ALIASES


def parse_project_platform(text: str) -> tuple[str | None, str | None]:
    """Parse project and platform from user input like 'личный тг'."""
    words = text.lower().split()
    project_id = None
    platform = None

    # Try two-word brand names first
    for i in range(len(words) - 1):
        two_word = f"{words[i]} {words[i+1]}"
        if two_word in BRAND_ALIASES:
            project_id = BRAND_ALIASES[two_word]
            break

    # Then single-word
    if not project_id:
        for w in words:
            if w in BRAND_ALIASES:
                project_id = BRAND_ALIASES[w]
                break

    for w in words:
        if w in PLATFORM_ALIASES:
            platform = PLATFORM_ALIASES[w]
            break

    return project_id, platform


def format_post_card(post: dict) -> str:
    """Format a post draft as a readable card for the admin."""
    brand = BRANDS.get(post["project_id"], {})
    brand_name = brand.get("name", post["project_id"])
    status_emoji = {
        "draft": "📝", "approved": "✅", "published": "📢",
        "rejected": "❌", "error": "⚠️",
    }.get(post["status"], "📋")

    lines = [
        f"{status_emoji} <b>#{post['id']} | {brand_name} | {post['platform']}</b>",
        f"Статус: {post['status']}",
        "",
        post["content"][:3500],
    ]
    return "\n".join(lines)


def split_message(text: str, limit: int = 4096) -> list[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= limit:
        return [text]

    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


def format_trends_card(trends: list[dict]) -> str:
    """Format today's trends for display."""
    if not trends:
        return "Трендов на сегодня пока нет."

    lines = ["<b>Тренды дня</b>", ""]
    for t in trends:
        brand = BRANDS.get(t["project_id"], {})
        brand_name = brand.get("name", t["project_id"])
        lines.append(f"<b>{brand_name}</b>")
        lines.append(f"  Тренд: {t.get('trend', '—')}")
        lines.append(f"  Идея: {t.get('idea', '—')}")
        lines.append("")
    return "\n".join(lines)
