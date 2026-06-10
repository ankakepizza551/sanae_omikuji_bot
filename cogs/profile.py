import discord
from discord.ext import commands
from utils.database import get_user, get_omikuji_stats

def get_faith_title(favorability: int) -> str:
    """好感度(信仰度)に応じた称号を取得"""
    if favorability < 50:
        return "一般参拝客"
    elif favorability < 150:
        return "守矢の小信仰者"
    elif favorability < 300:
        return "熱心な参拝者"
    elif favorability < 500:
        return "守矢の熱狂的信者"
    elif favorability < 800:
        return "奇跡の目撃者"
    elif favorability < 1000:
        return "神徳を宿す者"
    else:
        return "早苗の親友（常識を捨てし者）"

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="profile", description="あなたの参拝記録と早苗との信仰度ステータスを表示します")
    async def profile(self, ctx):
        """ユーザープロファイルを表示"""
        user_id = ctx.author.id
        user_name = ctx.author.display_name
        
        user = await get_user(user_id, user_name)
        stats = await get_omikuji_stats(user_id)
        
        # 称号の取得
        title = get_faith_title(user["favorability"])
        
        # 好感度のプログレスバー表示
        bar_length = 10
        fav_val = min(1000, user["favorability"])
        filled_length = int(bar_length * fav_val / 1000)
        bar = "🟢" * filled_length + "⚪" * (bar_length - filled_length)
        
        # おみくじ統計テキストの生成
        stats_text = ""
        if stats:
            for fortune, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                stats_text += f"• **{fortune}**: `{count}` 回\n"
        else:
            stats_text = "*まだおみくじを引いていません*"
            
        embed = discord.Embed(
            title=f"⛩️ {user_name} 殿の守矢神社参拝手帳 ⛩️",
            color=discord.Color.from_rgb(15, 125, 66)
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        embed.add_field(
            name="信仰ステータス",
            value=f"**称号:** 【`{title}`】\n"
                  f"**早苗の好感度:** `{user['favorability']}` / 1000\n"
                  f"**ゲージ:** {bar}\n"
                  f"**連続参拝記録:** `{user['consecutive_days']}` 日連続",
            inline=False
        )
        
        embed.add_field(
            name="参拝記録",
            value=f"**累計おみくじ:** `{user['total_omikuji']}` 回\n"
                  f"**累計お賽銭額:** `{user['total_offerings']}` コイン",
            inline=True
        )
        
        embed.add_field(
            name="おみくじの内訳",
            value=stats_text,
            inline=True
        )
        
        # 早苗からのひと言
        comment = ""
        if user["favorability"] < 50:
            comment = "「守矢神社へようこそ！ぜひ毎日おみくじを引きに来てくださいね！」"
        elif user["favorability"] < 150:
            comment = "「少しずつ信仰が深まってきましたね。この調子ですよ！」"
        elif user["favorability"] < 300:
            comment = "「いつもお参りありがとうございます。あなたの願い、神様にしっかり届けておきます！」"
        elif user["favorability"] < 500:
            comment = "「もうすっかり熱心な信者さんですね！私とも息が合ってきた気がします！」"
        elif user["favorability"] < 800:
            comment = "「あなたの周りでたくさんの奇跡が起きているはずです。いつも感謝していますよ！」"
        elif user["favorability"] < 1000:
            comment = "「あなたの存在自体が私にとっての奇跡のようです。これからも守矢をよろしくお願いします！」"
        else:
            comment = "「あなたはもう常識に囚われない、私の大切な親友です！いつでも頼ってくださいね！」"
            
        embed.add_field(
            name="早苗からの言葉",
            value=comment,
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
