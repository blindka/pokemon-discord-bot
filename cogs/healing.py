"""
cogs/healing.py — מרכז רפואה (!heal)
"""
import discord
from discord.ext import commands

from database import db
from utils.pokemon_utils import get_pokemon_by_id


class HealingCog(commands.Cog, name="Healing"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="heal", aliases=["רפא", "healall", "pokecenter", "pc"])
    async def heal(self, ctx: commands.Context):
        """
        !heal — רפא את כל הפוקימונים בשישייה (חינם!)
        """
        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)

        if not user or not user["starter_selected"]:
            await ctx.send("❌ כתוב `!start` כדי להתחיל.")
            return

        team = await db.get_team(discord_id)
        if not team:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ אין פוקימונים",
                    description="אין לך פוקימונים לרפא!",
                    color=0xFF4444
                )
            )
            return

        # בדיקה אם יש מה לרפא
        needs_healing = any(t["current_hp"] < t["max_hp"] for t in team)
        if not needs_healing:
            await ctx.send(
                embed=discord.Embed(
                    title="💚 כולם בריאים!",
                    description="כל הפוקימונים שלך כבר בחיים מלאים!",
                    color=0x00C851
                )
            )
            return

        # ריפוי
        await db.heal_all_team(discord_id)

        embed = discord.Embed(
            title="🏥 מרכז הרפואה של פוקימון",
            description="✅ **כל הפוקימונים שלך נרפאו!**\n\nG ✨ הם מרגישים טוב!",
            color=0xFF69B4
        )

        # הצג את הצוות אחרי ריפוי
        healed_lines = []
        for entry in team:
            pdata = get_pokemon_by_id(entry["pokemon_id"])
            if pdata:
                healed_lines.append(f"💚 **{pdata['name']}** — HP: {entry['max_hp']}/{entry['max_hp']}")

        if healed_lines:
            embed.add_field(
                name="🐾 צוות מרופא:",
                value="\n".join(healed_lines),
                inline=False
            )

        embed.set_footer(text="כתוב !battle כדי לחזור לפעולה!")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HealingCog(bot))
