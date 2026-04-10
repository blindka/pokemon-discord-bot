"""
cogs/starter.py — בחירת פוקימון ראשוני (!start)
"""
import discord
from discord.ext import commands
import asyncio

from database import db
from utils.pokemon_utils import get_pokemon_by_id, get_starters
from utils.embed_utils import build_starter_embed, build_pokemon_embed
from config import STARTING_ITEMS, NUMBER_EMOJIS


class StarterCog(commands.Cog, name="Starter"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="start", aliases=["התחל", "begin"])
    async def start(self, ctx: commands.Context):
        """
        !start — מתחיל את המשחק ובוחר פוקימון התחלתי
        """
        discord_id = str(ctx.author.id)
        username = str(ctx.author.name)

        # יצירת משתמש אם לא קיים
        await db.create_user(discord_id, username)
        user = await db.get_user(discord_id)

        if user and user["starter_selected"]:
            await ctx.send(
                embed=discord.Embed(
                    title="✅ כבר התחלת!",
                    description=(
                        "כבר בחרת פוקימון התחלתי.\n"
                        "הפקודות הזמינות:\n"
                        "`!profile` — ראה את הפרופיל שלך\n"
                        "`!battle` — התחל קרב\n"
                        "`!team` — ראה את השישייה שלך\n"
                        "`!store` — כנס לחנות\n"
                        "`!help` — רשימת כל הפקודות"
                    ),
                    color=0x00C851
                )
            )
            return

        # בניית embed לבחירה
        embed, emojis = build_starter_embed()
        msg = await ctx.send(embed=embed)

        # הוספת ריאקציות
        for emoji in emojis:
            await msg.add_reaction(emoji)

        def check(reaction, user_reacted):
            return (
                user_reacted.id == ctx.author.id
                and str(reaction.emoji) in emojis
                and reaction.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await msg.edit(
                embed=discord.Embed(
                    title="⏰ פג הזמן!",
                    description="לא בחרת פוקימון בתוך 60 שניות. כתוב `!start` שוב.",
                    color=0xFF4444
                )
            )
            await msg.clear_reactions()
            return

        # מאפיין ID לפי מיקום הריאקציה
        chosen_index = emojis.index(str(reaction.emoji))
        starters = get_starters()
        chosen_pokemon = starters[chosen_index]

        if not chosen_pokemon:
            await ctx.send("❌ שגיאה במציאת הפוקימון. נסה שוב.")
            return

        # שמירה למסד הנתונים
        success = await db.add_to_team(
            discord_id,
            chosen_pokemon["id"],
            chosen_pokemon["hp"],
            level=5
        )
        await db.set_starter_selected(discord_id)
        await db.add_to_pokedex(discord_id, chosen_pokemon["id"])

        # הוספת פריטים התחלתיים
        for item_name, qty in STARTING_ITEMS.items():
            await db.add_item(discord_id, item_name, qty)

        # עדכון embed
        success_embed = discord.Embed(
            title=f"🎉 בחרת את {chosen_pokemon['name']}!",
            description=(
                f"**{chosen_pokemon['name']}** הצטרף לצוות שלך!\n\n"
                f"קיבלת גם **5 Poké Balls** כדי להתחיל.\n\n"
                "**מה עכשיו?**\n"
                "`!battle` — התחל קרב עם פוקימון פראי\n"
                "`!profile` — ראה את הפרופיל שלך\n"
                "`!store` — קנה ציוד\n"
                "`!pokedex <שם>` — חפש מידע על פוקימון"
            ),
            color=0xFFD700
        )
        success_embed.set_thumbnail(
            url=f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{chosen_pokemon['id']}.png"
        )
        await msg.clear_reactions()
        await msg.edit(embed=success_embed)


async def setup(bot):
    await bot.add_cog(StarterCog(bot))
