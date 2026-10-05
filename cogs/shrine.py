import discord
from discord.ext import commands
from utils.database import get_user, add_offering, get_today

# 1回のお賽銭の上限 (一万円札1枚ぶん)
MAX_OFFERING = 10_000

class ShrineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="moriya", description="守矢神社にお賽銭を奉納します（1日1回限定）")
    async def moriya(self, ctx, amount: int = 5):
        """お賽銭をあげるコマンド"""
        user_id = ctx.author.id
        user_name = ctx.author.display_name
        
        if amount <= 0:
            await ctx.send("❌ お賽銭は1枚以上入れてくださいね！")
            return

        if amount > MAX_OFFERING:
            await ctx.send(f"❌ お賽銭は一度に {MAX_OFFERING:,} 円までですよ！ お気持ちだけありがたくいただきますね！")
            return

        user = await get_user(user_id, user_name)
        today_str = get_today().isoformat()

        # クールダウンチェック (1日1回)
        if user["last_offering_date"] == today_str:
            await self._send_already_offered(ctx)
            return
            
        # 金額に応じた好感度の計算と早苗のメッセージ
        if amount < 10:
            gain = 1
            response = (
                f"「お、お気持ちだけで十分嬉しいですよ！ {amount}円ですね。\n"
                f"守矢の神々もきっとあなたのことを見ていてくださいます！」"
            )
        elif amount < 100:
            gain = 5
            response = (
                f"「お賽銭ありがとうございます！ {amount}円ですね。\n"
                f"これで守矢神社も少し潤います！ 良いことがありますように！」"
            )
        elif amount < 1000:
            gain = 12
            response = (
                f"「わあ！ {amount}円もいただけるなんて！\n"
                f"守矢神社を代表して、私、東風谷早苗が心よりお礼申し上げます！\n"
                f"あなたに神々のご加護がありますように！」"
            )
        else:
            gain = 25
            response = (
                f"「こんなにたくさん（{amount}円）良いのですか！？\n"
                f"ふふっ、博麗神社にお賽銭を入れるより、絶対にうち（守矢）に入れた方がお得ですよ！\n"
                f"さあ、常識にとらわれない奇跡を今すぐお祈りしましょう！」"
            )
            
        # DB更新 (同時に複数回実行された場合、2回目以降は None が返る)
        db_res = await add_offering(user_id, user_name, amount, gain)
        if db_res is None:
            await self._send_already_offered(ctx)
            return

        embed = discord.Embed(
            title="⛩️ 守矢神社 拝殿 ⛩️",
            description=f"{ctx.author.mention} さんがお賽銭箱に **{amount}** 円を投げ入れました。\n\n"
                        f"**早苗:**\n{response}\n\n"
                        f"早苗からの信仰度: `+{gain}` (現在: `{db_res['new_favorability']}`)\n"
                        f"これまでの累計お賽銭額: `{db_res['new_offerings']}` 円",
            color=discord.Color.from_rgb(15, 125, 66)
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    async def _send_already_offered(self, ctx):
        embed = discord.Embed(
            title="今日のお賽銭はすでに終わっています",
            description="お賽銭は1日1回までですよ！\nあまり欲張ると神様のバチが当たるかもしれませんよ？\nまた明日お参りに来てくださいね！",
            color=discord.Color.from_rgb(15, 125, 66)
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ShrineCog(bot))
