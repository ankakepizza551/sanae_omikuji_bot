import discord
from discord.ext import commands
import datetime
import random
from utils.database import get_user, use_miracle_db

class MiracleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="miracle", description="早苗に祈りを捧げ、1日1回の奇跡に挑戦します")
    async def miracle(self, ctx):
        """1日1回の奇跡挑戦ミニゲーム"""
        user_id = ctx.author.id
        user_name = ctx.author.display_name
        
        user = await get_user(user_id, user_name)
        today_str = datetime.date.today().isoformat()
        
        # クールダウンチェック (1日1回)
        if user["last_miracle_date"] == today_str:
            embed = discord.Embed(
                title="奇跡は安売りできません！",
                description="奇跡の挑戦は1日1回までですよ！\nそんなに何度も奇跡を起こしては、それはもう『常識』になってしまいます！\nまた明日、奇跡を信じて挑戦しに来てくださいね！",
                color=discord.Color.from_rgb(15, 125, 66)
            )
            await ctx.send(embed=embed)
            return
            
        # 成功率の計算: 基本20% + 好感度の0.05% (最大好感度1000で+50%、計70%)
        favorability = user["favorability"]
        base_rate = 0.20
        bonus_rate = favorability * 0.0005
        success_rate = min(0.80, base_rate + bonus_rate)  # 最大80%に制限
        
        # 判定
        is_success = random.random() < success_rate
        
        if is_success:
            gain = 50
            db_res = await use_miracle_db(user_id, user_name, gain)
            
            # 成功メッセージのバリエーション
            success_messages = [
                "「見てください！私の起こした奇跡です！風と雨があなたを祝福しています！」",
                "「やりました！守矢の神々の力が満ち溢れ、あなたに無限の幸運が舞い降りましたよ！」",
                "「これこそが奇跡です！常識を捨て去ったあなただからこそ、この祈りが届いたのですね！」"
            ]
            commentary = random.choice(success_messages)
            
            embed = discord.Embed(
                title="✨ 奇跡発生！ (Miracle Success) ✨",
                description=f"{ctx.author.mention} さんへの祈りが通じました！\n\n"
                            f"**早苗:**\n{commentary}\n\n"
                            f"早苗からの信頼・信仰度: `+{gain}` (現在: `{db_res['new_favorability']}`)\n"
                            f"成功確率だった値: `{int(success_rate * 100)}%`",
                color=discord.Color.from_rgb(212, 175, 55) # ゴールド枠
            )
            # 成功時の演出として大きなキラキラ星をサムネイルに
            embed.set_thumbnail(url="https://i.imgur.com/83pZp8X.png" if False else ctx.author.display_avatar.url)
            
        else:
            gain = 2  # 失敗しても少しだけ上がる
            db_res = await use_miracle_db(user_id, user_name, gain)
            
            # 失敗メッセージ
            fail_messages = [
                "「うぅ……ごめんなさい、少し祈りが足りなかったみたいです……。次は絶対に成功させますからね！」",
                "「あれっ？何も起きませんね……。お、おかしいです、常識的にはここで突風が吹くはずなのですが……！」",
                "「うーん、神様も今日はお昼寝中でしょうか？ でも、信仰度（好感度）は少しだけ上がりましたよ！」"
            ]
            commentary = random.choice(fail_messages)
            
            embed = discord.Embed(
                title="🍃 奇跡は起こらなかった…… 🍃",
                description=f"{ctx.author.mention} さんの挑戦は静かに幕を閉じました。\n\n"
                            f"**早苗:**\n{commentary}\n\n"
                            f"早苗からの信仰度: `+{gain}` (現在: `{db_res['new_favorability']}`)\n"
                            f"成功確率だった値: `{int(success_rate * 100)}%`",
                color=discord.Color.from_rgb(27, 49, 94) # 深い青枠
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MiracleCog(bot))
