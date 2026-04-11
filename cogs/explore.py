"""
cogs/explore.py — מערכת אזורים וסיור
"""
import discord
from discord.ext import commands
import asyncio

from database import db
from config import ZONES, DEFAULT_ZONE, NUMBER_EMOJIS


class ExploreCog(commands.Cog, name="Explore"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="explore", aliases=["מפה", "zone", "אזור"])
    async def explore(self, ctx: commands.Context):
        """!explore — בחר את אזור הסיור שלך"""
        discord_id = str(ctx.author.id)

        user = await db.get_user(discord_id)
        if not user or not user["starter_selected"]:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ טרם התחלת!",
                    description="כתוב `!start` כדי להתחיל.",
                    color=0xFF4444
                )
            )
            return

        current_zone = user.get("current_zone", DEFAULT_ZONE)
        zone_list = list(ZONES.items())

        embed = discord.Embed(
            title="🗺️ בחר אזור סיור",
            description=(
                f"**אזור נוכחי:** {ZONES.get(current_zone, {}).get('name', current_zone)}\n\n"
                "בחר אזור חדש — כל אזור מחזיר סוגי פוקימונים שונים!\n"
                "**70%** מפוקימוני האזור, **30%** אקראי."
            ),
            color=0x00AAFF
        )

        emojis = []
        for i, (zone_key, zone_data) in enumerate(zone_list):
            emoji = NUMBER_EMOJIS[i]
            is_current = "👈 **נוכחי**" if zone_key == current_zone else ""
            embed.add_field(
                name=f"{emoji} {zone_data['name']} {is_current}",
                value=_zone_description(zone_key),
                inline=True
            )
            emojis.append(emoji)

        embed.set_footer(text="לחץ על ריאקציה לשינוי האזור")
        msg = await ctx.send(embed=embed)

        # Add reactions in parallel
        await asyncio.gather(*[msg.add_reaction(e) for e in emojis])

        def check(r, u):
            return (
                u.id == ctx.author.id
                and str(r.emoji) in emojis
                and r.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return

        await msg.clear_reactions()
        chosen_idx = emojis.index(str(reaction.emoji))
        chosen_zone_key, chosen_zone_data = zone_list[chosen_idx]

        await db.set_zone(discord_id, chosen_zone_key)

        confirm_embed = discord.Embed(
            title=f"✅ עברת ל{chosen_zone_data['name']}!",
            description=(
                f"כעת הקרבות שלך יתרחשו ב**{chosen_zone_data['name']}**.\n"
                f"השתמש ב-`!battle` כדי להתחיל לחפש פוקימונים!"
            ),
            color=0x00FF00
        )
        await ctx.send(embed=confirm_embed)


def _zone_description(zone_key: str) -> str:
    descriptions = {
        "ocean":    "🐟 פוקימוני מים, Gyarados, Lapras...",
        "forest":   "🌱 Bulbasaur, Caterpie, Oddish...",
        "mountain": "🪨 Geodude, Machop, Onix...",
        "city":     "⚡ Pikachu, Abra, Meowth...",
        "cave":     "👻 Zubat, Gastly, Drowzee...",
        "grass":    "🐦 Pidgey, Ekans, Ponyta...",
    }
    return descriptions.get(zone_key, "...")


async def setup(bot):
    await bot.add_cog(ExploreCog(bot))
