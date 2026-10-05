import aiosqlite
import datetime
import os
import config

DB_PATH = config.DB_PATH

JST = datetime.timezone(datetime.timedelta(hours=9))

def get_today() -> datetime.date:
    """1日1回制限の基準日を返す。日本時間の0時に切り替わる"""
    return datetime.datetime.now(JST).date()

async def init_db():
    """データベースとテーブルの初期化"""
    async with aiosqlite.connect(DB_PATH) as db:
        # ユーザーテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                favorability INTEGER DEFAULT 0,
                total_omikuji INTEGER DEFAULT 0,
                consecutive_days INTEGER DEFAULT 0,
                last_omikuji_date TEXT,
                total_offerings INTEGER DEFAULT 0,
                last_offering_date TEXT,
                last_miracle_date TEXT
            )
        """)
        # おみくじ履歴テーブル (統計やログ用)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS omikuji_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                fortune TEXT,
                drawn_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 日付の基準をUTCから日本時間に変えた際の1回限りの移行。
        # 最後におみくじを引いた日を履歴の時刻から日本時間で付け直す
        # (これをしないと、日本時間0〜9時に引いていた人の連続参拝が途切れてしまう)
        async with db.execute("PRAGMA user_version") as cursor:
            version = (await cursor.fetchone())[0]
        if version < 1:
            await db.execute("""
                UPDATE users
                SET last_omikuji_date = (
                    SELECT date(MAX(datetime(drawn_at)), '+9 hours')
                    FROM omikuji_history WHERE user_id = users.user_id
                )
                WHERE last_omikuji_date IS NOT NULL
                  AND EXISTS (SELECT 1 FROM omikuji_history WHERE user_id = users.user_id)
            """)
            await db.execute("PRAGMA user_version = 1")
        await db.commit()

async def get_user(user_id: int, username: str = None):
    """ユーザー情報を取得。存在しない場合は作成"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

        if user is None:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username or f"User {user_id}")
            )
            await db.commit()
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
        elif username and user["username"] != username:
            # ユーザー名が変更されていたら更新
            await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            await db.commit()
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()

        return user

async def draw_omikuji_db(user_id: int, username: str, fortune: str, favorability_gain: int) -> dict | None:
    """おみくじを引いた時のDB更新処理。今日すでに引いていた場合は何も更新せず None を返す"""
    today = get_today()
    today_str = today.isoformat()
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()
    await get_user(user_id, username)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # 1日1回の判定と更新を1文で行う (連打で2回引けてしまうのを防ぐ)
        cursor = await db.execute("""
            UPDATE users
            SET favorability = MAX(0, favorability + ?),
                total_omikuji = total_omikuji + 1,
                consecutive_days = CASE WHEN last_omikuji_date = ? THEN consecutive_days + 1 ELSE 1 END,
                last_omikuji_date = ?
            WHERE user_id = ? AND last_omikuji_date IS NOT ?
        """, (favorability_gain, yesterday_str, today_str, user_id, today_str))
        if cursor.rowcount == 0:
            return None

        # 履歴追加
        await db.execute(
            "INSERT INTO omikuji_history (user_id, fortune) VALUES (?, ?)",
            (user_id, fortune)
        )
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

    return {
        "consecutive_days": user["consecutive_days"],
        "new_favorability": user["favorability"],
        "total_omikuji": user["total_omikuji"]
    }

async def add_offering(user_id: int, username: str, amount: int, favorability_gain: int) -> dict | None:
    """お賽銭をした時のDB更新処理。今日すでに奉納していた場合は何も更新せず None を返す"""
    today_str = get_today().isoformat()
    await get_user(user_id, username)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            UPDATE users
            SET total_offerings = total_offerings + ?,
                favorability = MAX(0, favorability + ?),
                last_offering_date = ?
            WHERE user_id = ? AND last_offering_date IS NOT ?
        """, (amount, favorability_gain, today_str, user_id, today_str))
        if cursor.rowcount == 0:
            return None
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

    return {
        "new_offerings": user["total_offerings"],
        "new_favorability": user["favorability"]
    }

async def use_miracle_db(user_id: int, username: str, favorability_gain: int) -> dict | None:
    """奇跡コマンドを実行した時のDB更新処理。今日すでに挑戦していた場合は何も更新せず None を返す"""
    today_str = get_today().isoformat()
    await get_user(user_id, username)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            UPDATE users
            SET favorability = MAX(0, favorability + ?),
                last_miracle_date = ?
            WHERE user_id = ? AND last_miracle_date IS NOT ?
        """, (favorability_gain, today_str, user_id, today_str))
        if cursor.rowcount == 0:
            return None
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()

    return {
        "new_favorability": user["favorability"]
    }

async def reset_cooldown_db(user_id: int):
    """おみくじ・賽銭・奇跡の1日1回制限をリセットする (連続参拝記録は維持する)"""
    today = get_today()
    today_str = today.isoformat()
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        # 今日引いた分を「昨日引いた」状態に戻す。引き直しで連続日数が二重に増えないよう1日分戻しておく
        await db.execute("""
            UPDATE users
            SET consecutive_days = CASE WHEN last_omikuji_date = ? THEN MAX(0, consecutive_days - 1) ELSE consecutive_days END,
                last_omikuji_date = CASE WHEN last_omikuji_date = ? THEN ? ELSE last_omikuji_date END,
                last_offering_date = NULL,
                last_miracle_date = NULL
            WHERE user_id = ?
        """, (today_str, today_str, yesterday_str, user_id))
        await db.commit()

async def get_omikuji_stats(user_id: int) -> dict:
    """おみくじの統計情報を取得"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT fortune, COUNT(*) as count FROM omikuji_history WHERE user_id = ? GROUP BY fortune",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        stats = {row["fortune"]: row["count"] for row in rows}
        return stats
