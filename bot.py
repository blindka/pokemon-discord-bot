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
            help_command=None,
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
            "cogs.explore",
            "cogs.pvp",
            "cogs.admin",
            "cogs.game_logger",
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
            return
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
        value="`!start` — התחל את המשחק ובחר פוקימון ראשוני\n",
        inline=False
    )
    embed.add_field(
        name="⚔️ קרב פראי",
        value=(
            "`!battle` — קרב פוקימון פראי (לפי אזור!)\n"
            "◦ 1️⃣-4️⃣ בחר מהלך\n"
            "◦ 5️⃣ 🎒 מלאי | 6️⃣ 🔄 **החלף** (עולה תור!) | 7️⃣ 🏃 ברח\n"
            "◦ אם פוקימון נופל — בחר אחר מהשישייה\n"
        ),
        inline=False
    )
    embed.add_field(
        name="👥 קרב PvP",
        value=(
            "`!duel @שחקן` (או `!d`, `!challenge`) — אתגר שחקן אחר!\n"
            "◦ היריב מאשר עם ✅ או דוחה עם ❌\n"
            "◦ שני הצדדים בוחרים מהלך → מי שמהיר תוקף ראשון\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🗺️ מפה ואזורים / נדירות",
        value=(
            "`!explore` — בחר אזור (70% פוקימונים מהאזור)\n"
            "🌊 ים · 🌿 יער · ⛰️ הרים · 🏙️ עיר · 🕳️ מערה · 🌾 שדה\n"
            "**נדירות בטבע:** ⚪ נפוץ (60%) | 🟢 נדיר יחסית (25%) | 🔵 נדיר (12%) | 🟡 אגדי (3%)\n"
        ),
        inline=False
    )
    embed.add_field(
        name="⭐ XP ואבולוציה",
        value=(
            "• XP לפי נוסחת Gen 1: `(power × level) / 7`\n"
            "• עלייה ברמה → **אבולוציה אוטומטית!** ✨\n"
            "• פוקימונים פראיים מאוזנים לרמה שלך (-2 עד +5)\n"
        ),
        inline=False
    )
    embed.add_field(
        name="👤 פרופיל",
        value=(
            "`!profile` · `!team` · `!storage` · `!pokedex <שם>`\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🏪 חנות ומלאי",
        value=(
            "`!store` · `!buy <פריט>` · `!inventory` · `!use <פריט>`\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🏥 רפואה + 💰 כלכלה",
        value=(
            "`!heal` — רפא את כל הצוות (חינם!)\n"
            "• ניצחון = **Silver** + **XP** | תפוס פוקימונים = **פוקידקס**\n"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ ניהול (Admin)",
        value="`!adminhelp` — רשימת כל פקודות הניהול\n",
        inline=False
    )

    embed.set_footer(text="🎮 Pokémon Discord Bot | !start כדי להתחיל")
    await ctx.send(embed=embed)


# ===== SINGLE INSTANCE LOCK =====
import sys
import signal

PID_FILE = "bot.pid"

def _acquire_lock():
    """
    מונע הפעלת שני עותקים של הבוט במקביל.
    אם יש כבר instance חי — הורג אותו לפני שמתחיל.
    """
    current_pid = os.getpid()

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != current_pid:
                import psutil
                try:
                    proc = psutil.Process(old_pid)
                    proc.terminate()
                    proc.wait(timeout=3)
                    logger.warning(f"🛑 הרגנו instance ישן (PID {old_pid})")
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass  # כבר לא רץ
                except ImportError:
                    # psutil לא מותקן — ננסה דרך OS
                    try:
                        os.kill(old_pid, signal.SIGTERM)
                        logger.warning(f"🛑 שלחנו SIGTERM ל-PID {old_pid}")
                    except OSError:
                        pass
        except (ValueError, OSError):
            pass

    # כתוב את ה-PID הנוכחי
    with open(PID_FILE, "w") as f:
        f.write(str(current_pid))
    logger.info(f"🔒 Instance lock acquired (PID {current_pid})")


def _release_lock():
    """מנקה את קובץ ה-PID עם סגירת הבוט"""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                stored_pid = int(f.read().strip())
            if stored_pid == os.getpid():
                os.remove(PID_FILE)
                logger.info("🔓 Instance lock released")
    except Exception:
        pass


# ===== ENTRYPOINT =====
async def main():
    if BOT_TOKEN == "YOUR_TOKEN_HERE":
        logger.error("❌ TOKEN חסר! צור קובץ .env עם DISCORD_TOKEN=<הטוקן שלך>")
        return

    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    _acquire_lock()
    try:
        asyncio.run(main())
    finally:
        _release_lock()
