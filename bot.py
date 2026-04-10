"""
bot.py — נקודת הכניסה הראשית לבוט הדיסקורד
"""
import discord
from discord.ext import commands
import asyncio
import logging
import os

from config import BOT_TOKEN, PREFIX
from database.db import init_db

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("PokémonBot")

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True


class PokemonBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,  # Custom help
            case_insensitive=True,
        )

    async def setup_hook(self):
        """נקרא לפני החיבור — טעינת Cogs ובסיס הנתונים"""
        logger.info("🔧 Initializing database...")
        os.makedirs("data", exist_ok=True)
        await init_db()
        logger.info("✅ Database ready!")

        cogs = [
            "cogs.starter",
            "cogs.battle",
            "cogs.profile",
            "cogs.store",
            "cogs.inventory",
            "cogs.healing",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")

    async def on_ready(self):
        logger.info(f"🎮 {self.user.name} is online! (ID: {self.user.id})")
        logger.info(f"📡 Connected to {len(self.guilds)} guilds")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="!start | Pokémon Discord Bot"
            )
        )

    async def on_command_error(self, ctx: commands.Context, error):
        """טיפול גלובלי בשגיאות פקודות"""
        if isinstance(error, commands.CommandNotFound):
            return  # התעלם מפקודות לא קיימות
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=discord.Embed(
                    title="❌ שגיאה בפקודה",
                    description=f"חסר ארגומנט: **{error.param.name}**\n"
                                f"נסה `!help {ctx.command}`",
                    color=0xFF4444
                )
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=discord.Embed(
                    title="❌ ארגומנט לא תקין",
                    description=str(error),
                    color=0xFF4444
                )
            )
        else:
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ שגיאה פנימית",
                    description="משהו השתבש. נסה שוב.",
                    color=0xFF4444
                )
            )


bot = PokemonBot()


# ===== CUSTOM HELP =====
@bot.command(name="help", aliases=["עזרה", "commands"])
async def help_command(ctx: commands.Context):
    """!help — הצג את כל הפקודות"""
    embed = discord.Embed(
        title="📖 פקודות הבוט",
        description="📌 כל הפקודות מתחילות ב-`!`",
        color=0xFFD700
    )

    embed.add_field(
        name="🌟 התחלה",
        value=(
            "`!start` — התחל את המשחק ובחר פוקימון ראשוני\n"
        ),
        inline=False
    )
    embed.add_field(
        name="⚔️ קרב",
        value=(
            "`!battle` — התחל קרב עם פוקימון פראי אקראי\n"
            "◦ בחר מהלכים עם ריאקציות 1️⃣2️⃣3️⃣4️⃣\n"
            "◦ 5️⃣ פתח מלאי (להשתמש בפריט/לתפוס)\n"
            "◦ 6️⃣ ברח מהקרב\n"
        ),
        inline=False
    )
    embed.add_field(
        name="👤 פרופיל ושישייה",
        value=(
            "`!profile` — ראה סטטיסטיקות וצוות\n"
            "`!team` — ראה את השישייה המפורטת\n"
            "`!storage` — ראה את אחסון הפוקימונים\n"
            "`!pokedex <שם>` — מידע על פוקימון\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🏪 חנות ומלאי",
        value=(
            "`!store` — פתח את החנות\n"
            "`!buy <פריט>` — קנה פריט (למשל: `!buy Potion`)\n"
            "`!inventory` — ראה את המלאי שלך\n"
            "`!use <פריט>` — השתמש בתרופה\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🏥 מרכז רפואה",
        value="`!heal` — רפא את כל הפוקימונים (חינם!)\n",
        inline=False
    )
    embed.add_field(
        name="💰 כלכלה",
        value=(
            "• נצח בקרבות → **10-100 Silver**\n"
            "• תפוס פוקימונים → **מוסיף לפוקידקס**\n"
        ),
        inline=False
    )

    embed.set_footer(text="🎮 Pokémon Discord Bot | !start כדי להתחיל")
    await ctx.send(embed=embed)


# ===== ENTRYPOINT =====
async def main():
    if BOT_TOKEN == "YOUR_TOKEN_HERE":
        logger.error("❌ TOKEN חסר! צור קובץ .env עם DISCORD_TOKEN=<הטוקן שלך>")
        return

    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
