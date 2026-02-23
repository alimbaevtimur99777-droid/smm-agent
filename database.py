import logging
from datetime import datetime, timedelta

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                voice       TEXT,
                language    TEXT,
                audience    TEXT,
                goal        TEXT,
                topics      TEXT,
                forbidden   TEXT,
                platforms   TEXT,
                active      INTEGER NOT NULL DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trends (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                project_id  TEXT NOT NULL,
                trend       TEXT,
                idea        TEXT,
                category    TEXT,
                raw_trends  TEXT,
                created_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      TEXT NOT NULL,
                platform        TEXT NOT NULL,
                content         TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'draft',
                category        TEXT,
                scheduled_date  TEXT,
                published_at    TEXT,
                message_id      INTEGER,
                admin_message_id INTEGER,
                created_at      TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  TEXT,
                type        TEXT,
                insight     TEXT NOT NULL,
                evidence    TEXT,
                applied     INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start  TEXT NOT NULL,
                week_end    TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS competitor_insights (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                hot_topics  TEXT,
                content_gaps TEXT,
                best_formats TEXT,
                opportunities TEXT,
                urgent_alert TEXT,
                raw_data    TEXT,
                created_at  TEXT NOT NULL
            )
        """)
        await db.commit()
    logger.info("Database initialized")


# ── Projects ────────────────────────────────────────────────

async def upsert_project(project_id: str, data: dict):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO projects (id, name, voice, language, audience, goal, topics, forbidden, platforms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, voice=excluded.voice, language=excluded.language,
                audience=excluded.audience, goal=excluded.goal, topics=excluded.topics,
                forbidden=excluded.forbidden, platforms=excluded.platforms
        """, (
            project_id, data["name"], data.get("voice", ""), data.get("language", ""),
            data.get("audience", ""), data.get("goal", ""), data.get("topics", ""),
            data.get("forbidden", ""), ",".join(data.get("platforms", [])),
        ))
        await db.commit()


async def get_active_projects() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects WHERE active = 1")
        return [dict(r) for r in await cursor.fetchall()]


# ── Trends ──────────────────────────────────────────────────

async def save_trend(date: str, project_id: str, trend: str, idea: str,
                     category: str = "", raw_trends: str = ""):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO trends (date, project_id, trend, idea, category, raw_trends, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, project_id, trend, idea, category, raw_trends, now))
        await db.commit()


async def get_today_trends(date: str = None) -> list[dict]:
    date = date or datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM trends WHERE date = ? ORDER BY project_id", (date,)
        )
        return [dict(r) for r in await cursor.fetchall()]


# ── Posts ───────────────────────────────────────────────────

async def create_post(project_id: str, platform: str, content: str,
                      category: str = "trend", scheduled_date: str = None) -> int:
    now = datetime.now()
    scheduled_date = scheduled_date or now.strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO posts (project_id, platform, content, status, category, scheduled_date, created_at)
            VALUES (?, ?, ?, 'draft', ?, ?, ?)
        """, (project_id, platform, content, category, scheduled_date, now.isoformat()))
        await db.commit()
        return cursor.lastrowid


async def get_post(post_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_post_status(post_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "published":
            await db.execute(
                "UPDATE posts SET status = ?, published_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), post_id)
            )
        else:
            await db.execute(
                "UPDATE posts SET status = ? WHERE id = ?", (status, post_id)
            )
        await db.commit()


async def update_post_content(post_id: int, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
        await db.commit()


async def set_post_admin_message_id(post_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE posts SET admin_message_id = ? WHERE id = ?", (message_id, post_id)
        )
        await db.commit()


async def set_post_channel_message_id(post_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE posts SET message_id = ? WHERE id = ?", (message_id, post_id)
        )
        await db.commit()


async def get_approved_posts(date: str = None) -> list[dict]:
    date = date or datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM posts WHERE status = 'approved' AND scheduled_date = ?", (date,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_drafts() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM posts WHERE status = 'draft' ORDER BY created_at DESC"
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_recent_posts(project_id: str, limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM posts
            WHERE project_id = ? AND status = 'published'
            ORDER BY published_at DESC LIMIT ?
        """, (project_id, limit))
        return [dict(r) for r in await cursor.fetchall()]


async def get_posts_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        for status in ("draft", "approved", "published", "rejected"):
            c = await db.execute("SELECT COUNT(*) FROM posts WHERE status = ?", (status,))
            stats[status] = (await c.fetchone())[0]
        c = await db.execute("SELECT COUNT(*) FROM posts")
        stats["total"] = (await c.fetchone())[0]
        return stats


async def get_published_posts_for_week() -> list[dict]:
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM posts
            WHERE status = 'published' AND published_at >= ?
            ORDER BY published_at DESC
        """, (week_ago,))
        return [dict(r) for r in await cursor.fetchall()]


# ── Knowledge Base ──────────────────────────────────────────

async def add_insight(project_id: str, insight_type: str, insight: str,
                      evidence: str = ""):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO knowledge_base (project_id, type, insight, evidence, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, insight_type, insight, evidence, now))
        await db.commit()


async def get_insights(project_id: str = None, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if project_id:
            cursor = await db.execute("""
                SELECT * FROM knowledge_base
                WHERE (project_id = ? OR project_id IS NULL) AND applied = 1
                ORDER BY created_at DESC LIMIT ?
            """, (project_id, limit))
        else:
            cursor = await db.execute("""
                SELECT * FROM knowledge_base WHERE applied = 1
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        return [dict(r) for r in await cursor.fetchall()]


# ── Reports ─────────────────────────────────────────────────

async def save_report(week_start: str, week_end: str, content: str) -> int:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO reports (week_start, week_end, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (week_start, week_end, content, now))
        await db.commit()
        return cursor.lastrowid


async def get_latest_report() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ── Competitor Insights ─────────────────────────────────────

async def save_competitor_insight(date: str, analysis: dict, raw_data: str = ""):
    import json
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO competitor_insights
                (date, hot_topics, content_gaps, best_formats, opportunities, urgent_alert, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            json.dumps(analysis.get("hot_topics", []), ensure_ascii=False),
            json.dumps(analysis.get("content_gaps", []), ensure_ascii=False),
            json.dumps(analysis.get("best_formats", []), ensure_ascii=False),
            json.dumps(analysis.get("our_opportunities", []), ensure_ascii=False),
            analysis.get("urgent_alert", ""),
            raw_data,
            now,
        ))
        await db.commit()


async def get_latest_competitor_insight() -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM competitor_insights ORDER BY created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
