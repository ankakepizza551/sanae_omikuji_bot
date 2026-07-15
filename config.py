import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

# Railway環境では必ず /app/data のVolumeにDBを置く。
# Volumeが未マウントのまま起動するとコンテナの一時ディスクに空DBが作られ、
# 再起動・再デプロイのたびにデータが消えてしまうため、未マウント時は起動を止める。
if "RAILWAY_ENVIRONMENT" in os.environ:
    if not os.path.isdir("/app/data"):
        raise RuntimeError(
            "RailwayのVolumeが /app/data にマウントされていません。"
            "Railwayダッシュボードの Volumes タブでこのサービスに"
            "マウントパス /app/data のVolumeを追加してから再起動してください。"
            "（このまま起動するとデータが保存されません）"
        )
    DB_PATH = "/app/data/sanae_omikuji.db"
else:
    DB_PATH = os.getenv("DB_PATH", "data/sanae_omikuji.db")
    # Create data directory if it doesn't exist（ローカル開発用）
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
