import discord
from discord.ext import commands
import datetime
import random
import os
from utils.database import get_user, draw_omikuji_db
from utils.image_generator import generate_omikuji_image

# おみくじデータの定義
FORTUNES = [
    {
        "fortune": "奇跡",
        "commentary": "奇跡が起きました！常識に囚われないあなたなら、きっとどんな願いも叶えられますよ！私が全力で応援します！",
        "item": "風祝の髪飾り（蛙と蛇）",
        "action": "信じる心を持って、空を仰ぎ見てみる",
        "weight": 5,
        "gain": 30
    },
    {
        "fortune": "常識無視",
        "commentary": "この幻想郷では常識に囚われてはいけないのですね！あなたの常識を覆すような、とてもエキサイティングな一日になりますよ！",
        "item": "すわこの帽子",
        "action": "何か一つ、いつもと全く違う行動をとってみる",
        "weight": 8,
        "gain": 20
    },
    {
        "fortune": "大吉",
        "commentary": "大吉です！今日のあなたは神風が吹くように絶好調ですよ！自信を持って、やりたいことに挑戦してくださいね！",
        "item": "お祓い棒（博麗神社風）",
        "action": "誰かに小さな奇跡（親切）を届ける",
        "weight": 15,
        "gain": 15
    },
    {
        "fortune": "中吉",
        "commentary": "中吉です！とても良い運気ですね。日々の感謝を忘れずにお参りすれば、神様もきっと見ていてくださいますよ！",
        "item": "守矢のお札",
        "action": "温かいお茶を飲んで、ゆっくり深呼吸する",
        "weight": 20,
        "gain": 10
    },
    {
        "fortune": "吉",
        "commentary": "吉です！安定した運勢ですね。こういう日こそ、コツコツと信仰（努力）を積み重ねるのが一番の近道ですよ！",
        "item": "乾坤の御柱（ミニチュア）",
        "action": "身の回りの整理整頓をして風通しを良くする",
        "weight": 25,
        "gain": 8
    },
    {
        "fortune": "小吉",
        "commentary": "小吉です。小さな幸せが身近に隠れているはずです。いつもは見過ごしてしまうような変化に目を向けてみましょう。",
        "item": "五円玉（ご縁がありますように）",
        "action": "道端の小さな自然や花に目を向けてみる",
        "weight": 20,
        "gain": 5
    },
    {
        "fortune": "末吉",
        "commentary": "末吉です。今は準備の時期。焦らずに、これから徐々に運気が上がっていくのを楽しみにしていてくださいね！",
        "item": "青いリボン",
        "action": "背筋をピシッと伸ばして歩いてみる",
        "weight": 15,
        "gain": 3
    },
    {
        "fortune": "凶",
        "commentary": "凶が出てしまいました……でも大丈夫！私が代わりに厄払いのお祈りをしておきますから、どうか気を落とさないでくださいね！",
        "item": "守矢の厄除け守り",
        "action": "今日は無茶をせず、お家で早めに眠る",
        "weight": 10,
        "gain": 2
    },
    {
        "fortune": "大凶",
        "commentary": "大凶……！？う、嘘ですよね……？で、でも、底まで落ちたらあとは上げるだけです！私がついていますから、奇跡を信じましょう！",
        "item": "早苗の手作りおはぎ",
        "action": "守矢神社にたくさんお賽銭をする（と運気が上がるかも？）",
        "weight": 5,
        "gain": 5
    }
]

class OmikujiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="omikuji", description="守矢神社のおみくじを引きます（1日1回限定）")
    async def omikuji(self, ctx):
        """1日1回引けるおみくじコマンド"""
        user_id = ctx.author.id
        user_name = ctx.author.display_name
        
        # ユーザー情報をDBから取得
        user = await get_user(user_id, user_name)
        today_str = datetime.date.today().isoformat()
        
        # クールダウンチェック (1日1回)
        if user["last_omikuji_date"] == today_str:
            embed = discord.Embed(
                title="おみくじは1日1回までですよ！",
                description=f"おみくじはすでに今日引かれています。\nまた明日引きに来てくださいね！\n\n**現在の連続参拝記録:** `{user['consecutive_days']}` 日連続",
                color=discord.Color.from_rgb(15, 125, 66)
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
            return

        # 応答中であることをDiscordに伝える (画像生成に時間がかかる場合があるため)
        await ctx.defer()
        
        # 重み付き抽選
        fortunes_choices = [f for f in FORTUNES]
        weights = [f["weight"] for f in FORTUNES]
        chosen = random.choices(fortunes_choices, weights=weights)[0]
        
        # DBを更新
        db_res = await draw_omikuji_db(
            user_id=user_id,
            username=user_name,
            fortune=chosen["fortune"],
            favorability_gain=chosen["gain"]
        )
        
        # 画像生成
        try:
            image_path = generate_omikuji_image(
                user_name=user_name,
                fortune=chosen["fortune"],
                commentary=chosen["commentary"],
                item=chosen["item"],
                action=chosen["action"],
                favorability=db_res["new_favorability"]
            )
        except Exception as e:
            await ctx.send(f"❌ おみくじの画像生成中にエラーが発生しました: {e}")
            return
            
        # 送信用のFileオブジェクト作成
        discord_file = discord.File(image_path, filename="omikuji.png")
        
        # メッセージの作成
        embed = discord.Embed(
            title="✨ 守矢神社おみくじ 結果 ✨",
            description=f"{ctx.author.mention} さんの今日の運勢は **{chosen['fortune']}** です！\n\n"
                        f"早苗からの信仰度: `+{chosen['gain']}` (現在: `{db_res['new_favorability']}`)\n"
                        f"連続参拝日数: `{db_res['consecutive_days']}` 日連続",
            color=discord.Color.from_rgb(15, 125, 66)
        )
        embed.set_image(url="attachment://omikuji.png")
        
        await ctx.send(file=discord_file, embed=embed)
        
        # 一時ファイルの削除 (Discord送信後は削除して良い)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"一時ファイルの削除失敗: {e}")

async def setup(bot):
    await bot.add_cog(OmikujiCog(bot))
