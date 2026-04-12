"""
cogs/admin.py — פקודות ניהול (Admin & Owner only)
"""
import discord
from discord.ext import commands
import asyncio
import logging
import os

from database.db import (
    get_user, reset_user, get_silver, set_silver,
    add_item, get_team, get_storage
)

logger = logging.getLogger("PokémonBot.Admin")

# ===== HELPERS =====

def admin_embed(title: str, description: str, color: int = 0x00BFFF) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="🛡️ Admin Panel")
    return embed


def error_embed(description: str) -> discord.Embed:
    return discord.Embed(title="❌ שגיאה", description=description, color=0xFF4444)


def success_embed(description: str) -> discord.Embed:
    return discord.Embed(title="✅ בוצע!", description=description, color=0x00CC66)


# ===== COG =====

class Admin(commands.Cog, name="Admin"):
    """🛡️ פקודות ניהול — Admin/Owner בלבד"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._maintenance = False   # מצב תחזוקה

    # ─────────────────────────────────────────────────────────────
    # OWNER ONLY
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="shutdown", aliases=["off", "כיבוי"])
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """!shutdown — כיבוי הבוט (Owner only)"""
        embed = admin_embed(
            "🔴 מכבה את הבוט...",
            f"הבוט כובה על ידי **{ctx.author.mention}**.\nלהתראות! 👋",
            color=0xFF4444
        )
        await ctx.send(embed=embed)
        logger.warning(f"🔴 Shutdown requested by {ctx.author} ({ctx.author.id})")
        await self.bot.close()

    @commands.command(name="reload", aliases=["rl"])
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, cog: str):
        """!reload <cog> — טעינה מחדש של Cog (Owner only)"""
        cog_path = f"cogs.{cog}"
        try:
            await self.bot.reload_extension(cog_path)
            await ctx.send(embed=success_embed(f"✅ **{cog}** נטען מחדש בהצלחה!"))
            logger.info(f"🔄 Reloaded {cog_path} by {ctx.author}")
        except commands.ExtensionNotLoaded:
            await ctx.send(embed=error_embed(f"`{cog}` לא היה טעון. מנסה לטעון..."))
            try:
                await self.bot.load_extension(cog_path)
                await ctx.send(embed=success_embed(f"✅ **{cog}** נטען בהצלחה!"))
            except Exception as e:
                await ctx.send(embed=error_embed(f"❌ נכשל: `{e}`"))
        except Exception as e:
            await ctx.send(embed=error_embed(f"❌ שגיאה בטעינה מחדש: `{e}`"))

    @commands.command(name="reloadall", aliases=["rla"])
    @commands.is_owner()
    async def reload_all(self, ctx: commands.Context):
        """!reloadall — טעינה מחדש של כל ה-Cogs (Owner only)"""
        cogs = [
            "cogs.starter", "cogs.battle", "cogs.profile",
            "cogs.store", "cogs.inventory", "cogs.healing",
            "cogs.explore", "cogs.pvp", "cogs.admin"
        ]
        results = []
        for cog in cogs:
            try:
                await self.bot.reload_extension(cog)
                results.append(f"✅ {cog.split('.')[-1]}")
            except Exception as e:
                results.append(f"❌ {cog.split('.')[-1]}: `{e}`")

        embed = admin_embed(
            "🔄 טעינה מחדש — כל ה-Cogs",
            "\n".join(results)
        )
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ADMIN ONLY
    # ─────────────────────────────────────────────────────────────

    @commands.command(name="maintenance", aliases=["maint", "תחזוקה"])
    @commands.has_permissions(administrator=True)
    async def maintenance(self, ctx: commands.Context):
        """!maintenance — הפעל/כבה מצב תחזוקה"""
        self._maintenance = not self._maintenance
        if self._maintenance:
            await self.bot.change_presence(
                status=discord.Status.dnd,
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="🔧 Maintenance Mode"
                )
            )
            embed = admin_embed(
                "🔧 מצב תחזוקה — פעיל",
                "הבוט במצב תחזוקה. פקודות עדיין זמינות לאדמינים.",
                color=0xFFA500
            )
        else:
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="!start | Pokémon Discord Bot"
                )
            )
            embed = admin_embed(
                "✅ מצב תחזוקה — כבוי",
                "הבוט חזר לפעילות רגילה.",
                color=0x00CC66
            )
        await ctx.send(embed=embed)

    @commands.command(name="resetuser", aliases=["reset_user", "ru"])
    @commands.has_permissions(administrator=True)
    async def reset_user_cmd(self, ctx: commands.Context, member: discord.Member):
        """!resetuser @משתמש — איפוס מלא של שחקן"""
        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נמצא במסד הנתונים."))
            return

        # אישור לפני מחיקה
        confirm_embed = discord.Embed(
            title="⚠️ אישור איפוס",
            description=(
                f"האם אתה בטוח שברצונך לאפס את **{member.display_name}**?\n\n"
                "פעולה זו תמחק:\n"
                "• 🐾 כל הפוקימונים (צוות + אחסון)\n"
                "• 💰 כל הכסף (Silver)\n"
                "• 🎒 כל המלאי\n"
                "• 📖 כל הפוקידקס\n\n"
                "✅ לאישור | ❌ לביטול"
            ),
            color=0xFF4444
        )
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user_r):
            return user_r == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.edit(embed=error_embed("⏰ פג תוקף — איפוס בוטל."))
            return

        if str(reaction.emoji) == "❌":
            await msg.edit(embed=error_embed("❌ איפוס בוטל."))
            return

        await reset_user(str(member.id))
        await msg.edit(embed=success_embed(
            f"✅ **{member.display_name}** אופס בהצלחה!\n"
            f"כל הנתונים נמחקו. השחקן יוכל להתחיל מחדש עם `!start`."
        ))
        logger.warning(f"🗑️ User {member} ({member.id}) was reset by {ctx.author} ({ctx.author.id})")

    @commands.command(name="resetserver", aliases=["rs", "reset_server"])
    @commands.has_permissions(administrator=True)
    async def reset_server_cmd(self, ctx: commands.Context):
        """!resetserver — איפוס כל השחקנים בשרת"""
        # אישור כפול לפני מחיקה
        confirm_embed = discord.Embed(
            title="🚨 אזהרה חמורה — איפוס שרת",
            description=(
                "פעולה זו תמחק את **כל** הנתונים של **כל** השחקנים בשרת!\n\n"
                "⚠️ **לא ניתן לשחזר!**\n\n"
                "הקלד `CONFIRM` בצ'אט תוך 30 שניות לאישור."
            ),
            color=0xFF0000
        )
        await ctx.send(embed=confirm_embed)

        def msg_check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() == "CONFIRM"

        try:
            await self.bot.wait_for("message", timeout=30.0, check=msg_check)
        except asyncio.TimeoutError:
            await ctx.send(embed=error_embed("⏰ פג תוקף — איפוס שרת בוטל."))
            return

        # איפוס כל חברי השרת שנמצאים בבסיס הנתונים
        guild_members = [str(m.id) for m in ctx.guild.members if not m.bot]
        count = 0
        for discord_id in guild_members:
            user = await get_user(discord_id)
            if user:
                await reset_user(discord_id)
                count += 1

        await ctx.send(embed=success_embed(
            f"✅ שרת **{ctx.guild.name}** אופס!\n"
            f"נמחקו נתונים של **{count}** שחקנים."
        ))
        logger.warning(f"🗑️ Server {ctx.guild.name} ({ctx.guild.id}) was reset by {ctx.author} ({ctx.author.id})")

    @commands.command(name="givesilver", aliases=["give", "addsilver"])
    @commands.has_permissions(administrator=True)
    async def give_silver(self, ctx: commands.Context, member: discord.Member, amount: int):
        """!givesilver @משתמש <כמות> — תוספת Silver לשחקן"""
        if amount <= 0:
            await ctx.send(embed=error_embed("הכמות חייבת להיות חיובית."))
            return

        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נרשם למשחק."))
            return

        from database.db import update_silver
        new_balance = await update_silver(str(member.id), amount)
        await ctx.send(embed=success_embed(
            f"💰 נוספו **{amount:,} Silver** ל-{member.mention}\n"
            f"יתרה חדשה: **{new_balance:,} Silver**"
        ))
        logger.info(f"💰 Gave {amount} silver to {member} by {ctx.author}")

    @commands.command(name="takesilver", aliases=["removeilver", "deductsilver"])
    @commands.has_permissions(administrator=True)
    async def take_silver(self, ctx: commands.Context, member: discord.Member, amount: int):
        """!takesilver @משתמש <כמות> — הסרת Silver משחקן"""
        if amount <= 0:
            await ctx.send(embed=error_embed("הכמות חייבת להיות חיובית."))
            return

        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נרשם למשחק."))
            return

        from database.db import update_silver
        new_balance = await update_silver(str(member.id), -amount)
        await ctx.send(embed=success_embed(
            f"💸 הוסרו **{amount:,} Silver** מ-{member.mention}\n"
            f"יתרה חדשה: **{new_balance:,} Silver**"
        ))
        logger.info(f"💸 Removed {amount} silver from {member} by {ctx.author}")

    @commands.command(name="setsilver")
    @commands.has_permissions(administrator=True)
    async def set_silver_cmd(self, ctx: commands.Context, member: discord.Member, amount: int):
        """!setsilver @משתמש <כמות> — קביעת Silver לשחקן לסכום מדויק"""
        if amount < 0:
            await ctx.send(embed=error_embed("הסכום לא יכול להיות שלילי."))
            return

        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נרשם למשחק."))
            return

        await set_silver(str(member.id), amount)
        await ctx.send(embed=success_embed(
            f"💰 יתרת **{member.mention}** הוגדרה ל-**{amount:,} Silver**"
        ))

    @commands.command(name="giveitem", aliases=["gi"])
    @commands.has_permissions(administrator=True)
    async def give_item(self, ctx: commands.Context, member: discord.Member, quantity: int, *, item_name: str):
        """!giveitem @משתמש <כמות> <פריט> — תוספת פריט לשחקן"""
        from config import STORE_ITEMS
        # מצא פריט (case-insensitive)
        matched = next(
            (name for name in STORE_ITEMS if name.lower() == item_name.lower()), None
        )
        if not matched:
            items_list = ", ".join(f"`{i}`" for i in STORE_ITEMS)
            await ctx.send(embed=error_embed(f"פריט לא קיים. פריטים זמינים:\n{items_list}"))
            return

        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נרשם למשחק."))
            return

        await add_item(str(member.id), matched, quantity)
        emoji = STORE_ITEMS[matched].get("emoji", "📦")
        await ctx.send(embed=success_embed(
            f"{emoji} נוספו **{quantity}x {matched}** ל-{member.mention}"
        ))

    @commands.command(name="userinfo", aliases=["ui", "playerinfo"])
    @commands.has_permissions(administrator=True)
    async def user_info(self, ctx: commands.Context, member: discord.Member):
        """!userinfo @משתמש — מידע על שחקן"""
        user = await get_user(str(member.id))
        if not user:
            await ctx.send(embed=error_embed(f"{member.mention} לא נרשם למשחק."))
            return

        team = await get_team(str(member.id))
        storage = await get_storage(str(member.id))
        import json
        pokedex = json.loads(user.get("pokedex_ids", "[]"))

        embed = discord.Embed(
            title=f"🔍 מידע על {member.display_name}",
            color=0x7289DA
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 Discord ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="💰 Silver", value=f"{user.get('silver', 0):,}", inline=True)
        embed.add_field(name="⚔️ קרבות", value=str(user.get("total_battles", 0)), inline=True)
        embed.add_field(name="🐾 צוות", value=f"{len(team)}/6 פוקימונים", inline=True)
        embed.add_field(name="📦 אחסון", value=f"{len(storage)} פוקימונים", inline=True)
        embed.add_field(name="📖 פוקידקס", value=f"{len(pokedex)} רשומות", inline=True)
        embed.add_field(
            name="🗺️ אזור נוכחי",
            value=user.get("current_zone", "grass"),
            inline=True
        )
        embed.add_field(
            name="🆕 הצטרף",
            value=str(user.get("created_at", "לא ידוע")),
            inline=False
        )
        embed.set_footer(text="🛡️ Admin Panel")
        await ctx.send(embed=embed)

    @commands.command(name="botinfo", aliases=["bi", "status"])
    @commands.has_permissions(administrator=True)
    async def bot_info(self, ctx: commands.Context):
        """!botinfo — מידע על הבוט"""
        from config import BOT_VERSION
        embed = discord.Embed(
            title="🤖 Pokémon Bot — מידע",
            color=0xFFD700
        )
        embed.add_field(name="📌 גרסה", value=BOT_VERSION, inline=True)
        embed.add_field(name="📡 סרברים", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(
            name="👥 משתמשים",
            value=str(sum(g.member_count for g in self.bot.guilds)),
            inline=True
        )
        embed.add_field(
            name="📋 Cogs טעונים",
            value=str(len(self.bot.cogs)),
            inline=True
        )
        embed.add_field(
            name="📟 פקודות",
            value=str(len(self.bot.commands)),
            inline=True
        )
        embed.add_field(
            name="🔧 מצב תחזוקה",
            value="✅ פעיל" if self._maintenance else "❌ כבוי",
            inline=True
        )
        embed.set_footer(text="🛡️ Admin Panel")
        await ctx.send(embed=embed)

    @commands.command(name="adminhelp", aliases=["ah"])
    @commands.has_permissions(administrator=True)
    async def admin_help(self, ctx: commands.Context):
        """!adminhelp — רשימת פקודות ניהול"""
        embed = discord.Embed(
            title="🛡️ פקודות ניהול",
            description="פקודות זמינות לאדמינים ובעלי הבוט",
            color=0x00BFFF
        )
        embed.add_field(
            name="👑 Owner בלבד",
            value=(
                "`!shutdown` / `!off` — כיבוי הבוט\n"
                "`!reload <cog>` — טעינה מחדש של cog\n"
                "`!reloadall` — טעינה מחדש של כל ה-cogs\n"
            ),
            inline=False
        )
        embed.add_field(
            name="🛡️ Admin",
            value=(
                "`!maintenance` — הפעל/כבה מצב תחזוקה\n"
                "`!resetuser @user` — איפוס שחקן\n"
                "`!resetserver` — איפוס כל השרת\n"
                "`!givesilver @user <כמות>` — תוספת כסף\n"
                "`!takesilver @user <כמות>` — הורדת כסף\n"
                "`!setsilver @user <כמות>` — קביעת כסף\n"
                "`!giveitem @user <כמות> <פריט>` — תוספת פריט\n"
                "`!userinfo @user` — מידע על שחקן\n"
                "`!botinfo` — מידע על הבוט\n"
            ),
            inline=False
        )
        embed.set_footer(text="🛡️ Admin Panel | Owner = בעל הבוט ב-Discord")
        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────────────────────
    # ERROR HANDLERS
    # ─────────────────────────────────────────────────────────────

    @shutdown.error
    @reload_cog.error
    @reload_all.error
    async def owner_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send(embed=error_embed("🚫 פקודה זו זמינה לבעל הבוט בלבד."))

    @reset_user_cmd.error
    @reset_server_cmd.error
    @give_silver.error
    @take_silver.error
    @set_silver_cmd.error
    @give_item.error
    @user_info.error
    @bot_info.error
    @admin_help.error
    @maintenance.error
    async def admin_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=error_embed("🚫 אין לך הרשאות אדמין."))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=error_embed("❌ משתמש לא נמצא."))
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=error_embed(f"❌ ארגומנט לא תקין: `{error}`"))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
