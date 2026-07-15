"""
消失した users / omikuji_history テーブルを、Discordのメッセージ履歴から
抽出した history_events.json (fetch_omikuji_history.py で生成) をもとに復元する
ワンショットスクリプト。

各コマンド(!omikuji, !moriya, !miracle, !profile)は実行のたびに
「現在の好感度」「連続参拝日数」「累計おみくじ回数」「累計お賽銭額」を含む
公開埋め込みメッセージを投稿していたため、それらを走査して最新値を推定復元する。

再構築のルール:
- favorability（好感度）: 単調増加のため、見つかった報告値の最大値を採用
- consecutive_days（連続参拝日数）: 最も新しいタイムスタンプの報告値を採用
- total_omikuji（累計おみくじ回数）: profile報告値の最大値 と 実際に検出した
  おみくじ結果イベント数 の大きい方を採用
- total_offerings（累計お賽銭額）: 報告値の最大値を採用
- last_omikuji_date / last_offering_date / last_miracle_date: 該当イベントの
  最新タイムスタンプの日付
- omikuji_history: おみくじ結果イベント1件につき1行を復元（fortune, drawn_at）

使い方:
  1. python fetch_omikuji_history.py 相当の手順で history_events.json を生成済みであること
  2. ローカルDBに対して確認: python restore_omikuji.py --dry-run
  3. 問題なければ: python restore_omikuji.py
  4. 本番(Railway)には railway run python restore_omikuji.py で反映
再実行しても、既に総計以上のデータがあるユーザーはスキップ・上書きしないため冪等。
"""
import argparse
import asyncio
import collections
import json
import os

import aiosqlite

import config

EVENTS_PATH = os.path.join(os.path.dirname(__file__), "history_events.json")


def build_user_states(events):
    by_user = collections.defaultdict(list)
    for e in events:
        by_user[e["user_id"]].append(e)

    users = {}
    history_rows = []

    for uid, evs in by_user.items():
        favorability = 0
        consecutive_days = 0
        consecutive_ts = None
        total_omikuji_reported = 0
        total_offerings = 0
        last_omikuji_ts = None
        last_offering_ts = None
        last_miracle_ts = None
        username = None
        omikuji_count = 0

        for e in evs:
            ts = e["ts"]
            if e.get("favorability") is not None:
                favorability = max(favorability, e["favorability"])
            if e.get("total_offerings") is not None:
                total_offerings = max(total_offerings, e["total_offerings"])
            if e.get("total_omikuji") is not None:
                total_omikuji_reported = max(total_omikuji_reported, e["total_omikuji"])
            if e.get("username"):
                username = e["username"]

            if e.get("consecutive_days") is not None:
                if consecutive_ts is None or ts > consecutive_ts:
                    consecutive_ts = ts
                    consecutive_days = e["consecutive_days"]

            if e["type"] == "omikuji_draw":
                omikuji_count += 1
                if last_omikuji_ts is None or ts > last_omikuji_ts:
                    last_omikuji_ts = ts
                if e.get("fortune"):
                    history_rows.append((uid, e["fortune"], ts))
            elif e["type"] == "offering":
                if last_offering_ts is None or ts > last_offering_ts:
                    last_offering_ts = ts
            elif e["type"] == "miracle":
                if last_miracle_ts is None or ts > last_miracle_ts:
                    last_miracle_ts = ts

        users[uid] = {
            "username": username or f"User {uid}",
            "favorability": favorability,
            "consecutive_days": consecutive_days,
            "total_omikuji": max(total_omikuji_reported, omikuji_count),
            "total_offerings": total_offerings,
            "last_omikuji_date": last_omikuji_ts[:10] if last_omikuji_ts else None,
            "last_offering_date": last_offering_ts[:10] if last_offering_ts else None,
            "last_miracle_date": last_miracle_ts[:10] if last_miracle_ts else None,
        }

    return users, history_rows


async def restore(dry_run: bool):
    with open(EVENTS_PATH, encoding="utf-8") as f:
        events = json.load(f)

    users, history_rows = build_user_states(events)

    print(f"対象DB: {config.DB_PATH}")
    print(f"復元対象ユーザー数: {len(users)} / おみくじ履歴: {len(history_rows)}件\n")
    for uid, u in users.items():
        print(
            f"  user_id={uid} ({u['username']}): "
            f"好感度={u['favorability']}, 連続参拝={u['consecutive_days']}日, "
            f"累計おみくじ={u['total_omikuji']}, 累計お賽銭={u['total_offerings']}"
        )

    if dry_run:
        print("\n--dry-run のためDBへの書き込みは行いません。")
        return

    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        inserted_users, skipped_users = 0, 0

        for uid, u in users.items():
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (uid,)
            ) as cursor:
                existing = await cursor.fetchone()

            if existing is not None:
                print(f"  user_id={uid} は既にレコードが存在するためスキップ（上書きしません）")
                skipped_users += 1
                continue

            await db.execute(
                """
                INSERT INTO users (
                    user_id, username, favorability, total_omikuji,
                    consecutive_days, last_omikuji_date, total_offerings,
                    last_offering_date, last_miracle_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid, u["username"], u["favorability"], u["total_omikuji"],
                    u["consecutive_days"], u["last_omikuji_date"], u["total_offerings"],
                    u["last_offering_date"], u["last_miracle_date"],
                ),
            )
            inserted_users += 1
        await db.commit()

        inserted_history, skipped_history = 0, 0
        for uid, fortune, ts in history_rows:
            async with db.execute(
                "SELECT 1 FROM omikuji_history WHERE user_id = ? AND fortune = ? AND drawn_at = ?",
                (uid, fortune, ts),
            ) as cursor:
                exists = await cursor.fetchone()
            if exists:
                skipped_history += 1
                continue
            await db.execute(
                "INSERT INTO omikuji_history (user_id, fortune, drawn_at) VALUES (?, ?, ?)",
                (uid, fortune, ts),
            )
            inserted_history += 1
        await db.commit()

    print(
        f"\n完了: users 復元 {inserted_users} 件 / スキップ {skipped_users} 件、"
        f" omikuji_history 復元 {inserted_history} 件 / スキップ {skipped_history} 件"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DBに書き込まず内容だけ表示する")
    args = parser.parse_args()
    asyncio.run(restore(dry_run=args.dry_run))
