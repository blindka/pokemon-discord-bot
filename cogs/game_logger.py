"""
cogs/game_logger.py — לוג אירועי מערכת לחדר ה-logs
"""
import discord
from discord.ext import commands
import logging

from utils.log_utils import send_log
from config import BOT_VERSION

logger = logging.getLogger("PokémonBot.Logger")


class GameLoggerCog(commands.Cog, name="GameLogger"):
    """מאזין לאירועי מערכת ושולח אותם לחדר ה-logs"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """לוג כשהבוט עולה"""
        guild_count = len(self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds)

        await send_log(
            self.bot,
            category="system",
            title="הבוט עלה לאוויר!",
            description=f"**{self.bot.user.name}** מחובר ומוכן לפעולה.",
            fields=[
                ("📌 גרסה", BOT_VERSION, True),
                ("📡 שרתים", str(guild_count), True),
                ("👥 משתמשים", str(user_count), True),
                ("🧩 Cogs", str(len(self.bot.cogs)), True),
            ],
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """לוג שגיאות לא-מטופלות"""
        # התעלם משגיאות רגילות
        ignored = (
            commands.CommandNotFound,
            commands.MissingRequiredArgument,
            commands.BadArgument,
            commands.CheckFailure,
            commands.MissingPermissions,
            commands.NotOwner,
        )
        if isinstance(error, ignored):
            return

        # שגיאה לא צפויה — שלח ל-logs
        await send_log(
            self.bot,
            category="error",
            title="שגיאה לא מטופלת",
            description=f"```{type(error).__name__}: {error}```",
            fields=[
                ("פקודה", f"`!{ctx.command}`" if ctx.command else "לא ידוע", True),
                ("ערוץ", f"#{ctx.channel.name}", True),
                ("שרת", ctx.guild.name if ctx.guild else "DM", True),
            ],
            user=ctx.author,
        )


async def setup(bot):
    await bot.add_cog(GameLoggerCog(bot))
