import asyncio
import datetime
import logging
import os
import sqlite3
import tempfile
import discord
from discord.ext import commands
import config

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("SanaeOmikujiBot")

# ロードするCogの定義
COGS = [
    "cogs.omikuji",
    "cogs.shrine",
    "cogs.profile",
    "cogs.miracle"
]

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容インテント (プレフィックスコマンド用)
intents.guilds = True

# Botオブジェクトの作成
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot起動完了: {bot.user} (ID: {bot.user.id})")
    
    # 早苗らしいステータスメッセージを設定
    activity = discord.Game(name="守矢神社でお守り配り | !omikuji")
    await bot.change_presence(status=discord.Status.online, activity=activity)

@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx):
    """スラッシュコマンドを同期します (Botのオーナーのみ実行可能)"""
    await ctx.send("スラッシュコマンドを同期中...")
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ スラッシュコマンドを {len(synced)} 件同期しました！")
        logger.info(f"コマンド同期完了: {len(synced)} 件")
    except Exception as e:
        await ctx.send(f"❌ 同期中にエラーが発生しました: {e}")
        logger.error(f"コマンド同期失敗: {e}")

@bot.command(name="reset_cooldown")
@commands.is_owner()
async def reset_cooldown(ctx, member: discord.Member = None):
    """おみくじ・賽銭・奇跡のクールダウンをリセットします (Botのオーナー専用)"""
    target = member or ctx.author
    try:
        import aiosqlite
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(
                "UPDATE users SET last_omikuji_date = NULL, last_offering_date = NULL, last_miracle_date = NULL WHERE user_id = ?",
                (target.id,)
            )
            await db.commit()
        await ctx.send(f"✅ {target.mention} 殿の1日1回制限をリセットしました！再度お試しいただけます。")
    except Exception as e:
        await ctx.send(f"❌ リセット中にエラーが発生しました: {e}")

@bot.command(name="db_backup")
@commands.is_owner()
async def db_backup(ctx):
    """データベースのバックアップファイルをこのチャンネルに送信します (Botのオーナー専用)"""
    def make_backup() -> str:
        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"sanae_omikuji_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}.db",
        )
        src = sqlite3.connect(config.DB_PATH)
        try:
            dst = sqlite3.connect(tmp_path)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        return tmp_path

    await ctx.send("バックアップを作成中...")
    tmp_path = None
    try:
        tmp_path = await asyncio.to_thread(make_backup)
        await ctx.send(file=discord.File(tmp_path, filename="sanae_omikuji_backup.db"))
        logger.info(f"db_backup: by user={ctx.author.id}")
    except Exception as e:
        await ctx.send(f"❌ バックアップ中にエラーが発生しました: {e}")
        logger.error(f"db_backup失敗: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@bot.command(name="bot_status")
async def bot_status(ctx):
    """Botの現在のステータスを表示"""
    embed = discord.Embed(title="東風谷早苗おみくじBot ステータス", color=discord.Color.from_rgb(15, 125, 66))
    embed.add_field(name="接続中のサーバー数", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="応答速度 (Latency)", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="稼働中のCogs", value="\n".join(f"✅ {cog.replace('cogs.', '')}" for cog in COGS), inline=False)
    await ctx.send(embed=embed)

async def main():
    async with bot:
        # データベースの初期化
        from utils.database import init_db
        await init_db()
        logger.info("データベース初期化完了。")
        
        # Cogsのロード
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                logger.info(f"Cogロード成功: {cog}")
            except Exception as e:
                logger.error(f"Cogロード失敗 {cog}: {e}")
                
        # Botの起動
        logger.info("Bot接続開始...")
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
