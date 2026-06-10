import aiosqlite
import datetime
import os
import config

DB_PATH = config.DB_PATH

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
        await db.commit()

async def get_user(user_id: int, username: str = None):
    """ユーザー情報を取得。存在しない場合は作成"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            
        if user is None:
            await db.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
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

async def draw_omikuji_db(user_id: int, username: str, fortune: str, favorability_gain: int) -> dict:
    """おみくじを引いた時のDB更新処理 (1日制限チェックは呼び出し側で行う)"""
    today_str = datetime.date.today().isoformat()
    user = await get_user(user_id, username)
    
    last_date_str = user["last_omikuji_date"]
    consecutive = user["consecutive_days"]
    
    if last_date_str:
        last_date = datetime.date.fromisoformat(last_date_str)
        delta = datetime.date.today() - last_date
        if delta.days == 1:
            consecutive += 1
        elif delta.days > 1:
            consecutive = 1
    else:
        consecutive = 1
        
    new_favorability = max(0, user["favorability"] + favorability_gain)
    new_total_omikuji = user["total_omikuji"] + 1
    
    async with aiosqlite.connect(DB_PATH) as db:
        # ユーザーテーブル更新
        await db.execute("""
            UPDATE users 
            SET favorability = ?, 
                total_omikuji = ?, 
                consecutive_days = ?, 
                last_omikuji_date = ? 
            WHERE user_id = ?
        """, (new_favorability, new_total_omikuji, consecutive, today_str, user_id))
        
        # 履歴追加
        await db.execute(
            "INSERT INTO omikuji_history (user_id, fortune) VALUES (?, ?)",
            (user_id, fortune)
        )
        await db.commit()
        
    return {
        "consecutive_days": consecutive,
        "new_favorability": new_favorability,
        "total_omikuji": new_total_omikuji
    }

async def add_offering(user_id: int, username: str, amount: int, favorability_gain: int):
    """お賽銭をした時のDB更新処理"""
    today_str = datetime.date.today().isoformat()
    user = await get_user(user_id, username)
    
    new_offerings = user["total_offerings"] + amount
    new_favorability = max(0, user["favorability"] + favorability_gain)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET total_offerings = ?, 
                favorability = ?, 
                last_offering_date = ? 
            WHERE user_id = ?
        """, (new_offerings, new_favorability, today_str, user_id))
        await db.commit()
        
    return {
        "new_offerings": new_offerings,
        "new_favorability": new_favorability
    }

async def use_miracle_db(user_id: int, username: str, favorability_gain: int):
    """奇跡コマンドを実行した時のDB更新処理"""
    today_str = datetime.date.today().isoformat()
    user = await get_user(user_id, username)
    
    new_favorability = max(0, user["favorability"] + favorability_gain)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET favorability = ?, 
                last_miracle_date = ? 
            WHERE user_id = ?
        """, (new_favorability, today_str, user_id))
        await db.commit()
        
    return {
        "new_favorability": new_favorability
    }

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
