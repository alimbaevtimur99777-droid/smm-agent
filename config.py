import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "smm_agent.db")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

TIMEZONE = "Asia/Tashkent"

# Три бренда
BRANDS = {
    "personal_brand": {
        "name": "Личный Бренд",
        "voice": "вдохновляющий, честный, практичный",
        "language": "русский / узбекский",
        "audience": "предприниматели МСБ, начинающие маркетологи",
        "goal": "стать trusted экспертом, получать входящие запросы",
        "topics": "маркетинг, кейсы, ошибки, личная эффективность, бизнес-мышление",
        "forbidden": "агрессивные продажи, клише, хайп без пользы",
        "platforms": ["telegram", "instagram"],
    },
    "leader_team": {
        "name": "Лидер Тим",
        "voice": "деловой, экспертный, партнёрский",
        "language": "русский",
        "audience": "IT-директора, CTO, закупщики, интеграторы",
        "goal": "стать первым выбором при покупке телеком оборудования B2B",
        "topics": "решения для бизнеса, кейсы внедрения, ROI, телеком тренды",
        "forbidden": "развлекательный контент, личные темы, обещания без цифр",
        "platforms": ["telegram", "linkedin"],
    },
    "pixie": {
        "name": "Пикси",
        "voice": "технологичный, инновационный, инженерный",
        "language": "русский",
        "audience": "дистрибьюторы, системные интеграторы, телеком-операторы",
        "goal": "расширить дилерскую сеть, показать технологическое превосходство",
        "topics": "технологии, производственные стандарты, индустриальные тренды, партнёрство",
        "forbidden": "негативное сравнение с конкурентами, непроверенные заявления",
        "platforms": ["telegram", "facebook"],
    },
}

BRAND_ALIASES = {
    "личный": "personal_brand",
    "личный бренд": "personal_brand",
    "personal": "personal_brand",
    "лидер": "leader_team",
    "лидер тим": "leader_team",
    "leader": "leader_team",
    "пикси": "pixie",
    "pixie": "pixie",
}

PLATFORM_ALIASES = {
    "тг": "telegram",
    "телеграм": "telegram",
    "telegram": "telegram",
    "инста": "instagram",
    "инстаграм": "instagram",
    "instagram": "instagram",
    "фб": "facebook",
    "фейсбук": "facebook",
    "facebook": "facebook",
    "линкедин": "linkedin",
    "linkedin": "linkedin",
}
