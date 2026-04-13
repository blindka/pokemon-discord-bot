"""
cogs/store.py — חנות פוקימון (!store, !buy)
"""
import discord
from discord.ext import commands
import asyncio

from database import db
from utils.embed_utils import build_store_embed
from config import STORE_ITEMS, NUMBER_EMOJIS
from utils.log_utils import send_log


class StoreCog(commands.Cog, name="Store"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="store", aliases=["חנות", "shop", "market"])
    async def store(self, ctx: commands.Context):
        """!store — פתח את חנות הפוקימון"""
        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)

        if not user or not user["starter_selected"]:
            await ctx.send("❌ כתוב `!start` כדי להתחיל את המשחק.")
            return

        silver = user["silver"]
        embed = build_store_embed(silver)
        await ctx.send(embed=embed)

    @commands.command(name="buy", aliases=["קנה", "purchase"])
    async def buy(self, ctx: commands.Context, *, item_name: str = None):
        """
        !buy <שם פריט> — קנה פריט מהחנות
        דוגמה: !buy Potion
        """
        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)

        if not user or not user["starter_selected"]:
            await ctx.send("❌ כתוב `!start` כדי להתחיל את המשחק.")
            return

        if not item_name:
            # הצג תפריט אינטראקטיבי
            await self._interactive_buy(ctx, discord_id, user["silver"])
            return

        # חיפוש פריט לפי שם (case-insensitive)
        found_item = None
        found_key = None
        for key, info in STORE_ITEMS.items():
            if key.lower() == item_name.lower() or key.lower().replace(" ", "") == item_name.lower().replace(" ", ""):
                found_item = info
                found_key = key
                break

        if not found_item:
            # הצג תפריט אינטראקטיבי אם לא נמצא
            await ctx.send(
                embed=discord.Embed(
                    title="❌ פריט לא נמצא",
                    description=(
                        f"לא מצאתי פריט בשם **{item_name}**.\n\n"
                        "**פריטים זמינים:**\n" +
                        "\n".join(f"{v['emoji']} `{k}` — {v['price']} Silver" for k, v in STORE_ITEMS.items()) +
                        "\n\nדוגמה: `!buy Potion`"
                    ),
                    color=0xFF4444
                )
            )
            return

        # בדיקת מספיק כסף
        current_silver = await db.get_silver(discord_id)
        if current_silver < found_item["price"]:
            await ctx.send(
                embed=discord.Embed(
                    title="💸 אין מספיק Silver!",
                    description=(
                        f"**{found_key}** עולה **{found_item['price']} Silver**.\n"
                        f"יש לך רק **{current_silver} Silver**.\n\n"
                        "כדי להרוויח Silver — שחק `!battle`!"
                    ),
                    color=0xFF4444
                )
            )
            return

        # רכישה
        await db.update_silver(discord_id, -found_item["price"])
        await db.add_item(discord_id, found_key, 1)
        new_silver = await db.get_silver(discord_id)

        success_embed = discord.Embed(
            title=f"✅ קנית {found_item['emoji']} {found_key}!",
            description=(
                f"שילמת **{found_item['price']} Silver**.\n"
                f"יתרה: **{new_silver} Silver**\n\n"
                "הפריט נוסף למלאי שלך — `!inventory`"
            ),
            color=0x00C851
        )
        await ctx.send(embed=success_embed)

        # ── Log ──
        await send_log(
            ctx.bot,
            category="shop",
            title="רכישה בחנות",
            description=f"קנה {found_item['emoji']} **{found_key}** ב-**{found_item['price']} Silver**",
            fields=[("💰 יתרה", f"{new_silver} Silver", True)],
            user=ctx.author,
        )

    async def _interactive_buy(self, ctx, discord_id: str, silver: int):
        """תפריט קניה אינטראקטיבי עם ריאקציות"""
        items_list = list(STORE_ITEMS.items())
        embed = discord.Embed(
            title="🏪 מה תרצה לקנות?",
            description=f"💰 יתרה: **{silver} Silver**\n\nבחר פריט:",
            color=0x00C851
        )

        emojis = []
        for i, (name, info) in enumerate(items_list[:9]):
            emoji = NUMBER_EMOJIS[i]
            embed.add_field(
                name=f"{emoji} {info['emoji']} {name}",
                value=f"**{info['price']} Silver**",
                inline=True
            )
            emojis.append(emoji)

        cancel = "❌"
        embed.set_footer(text="❌ לביטול")
        msg = await ctx.send(embed=embed)
        for e in emojis:
            await msg.add_reaction(e)
        await msg.add_reaction(cancel)

        def check(r, u):
            return (
                u.id == ctx.author.id
                and (str(r.emoji) in emojis or str(r.emoji) == cancel)
                and r.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return

        chosen = str(reaction.emoji)
        await msg.delete()

        if chosen == cancel:
            return

        idx = emojis.index(chosen)
        item_key, item_info = items_list[idx]

        current_silver = await db.get_silver(discord_id)
        if current_silver < item_info["price"]:
            await ctx.send(
                embed=discord.Embed(
                    title="💸 אין מספיק Silver!",
                    description=f"**{item_key}** עולה **{item_info['price']} Silver**.\nיש לך **{current_silver} Silver**.",
                    color=0xFF4444
                )
            )
            return

        await db.update_silver(discord_id, -item_info["price"])
        await db.add_item(discord_id, item_key, 1)
        new_silver = await db.get_silver(discord_id)

        await ctx.send(
            embed=discord.Embed(
                title=f"✅ קנית {item_info['emoji']} {item_key}!",
                description=f"יתרה: **{new_silver} Silver**",
                color=0x00C851
            )
        )


async def setup(bot):
    await bot.add_cog(StoreCog(bot))
