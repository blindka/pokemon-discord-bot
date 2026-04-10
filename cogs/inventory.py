"""
cogs/inventory.py — מלאי (!inventory, !use)
"""
import discord
from discord.ext import commands
import asyncio
from typing import Optional, List

from database import db
from utils.embed_utils import build_inventory_embed
from utils.pokemon_utils import get_pokemon_by_id
from config import STORE_ITEMS, NUMBER_EMOJIS


class InventoryCog(commands.Cog, name="Inventory"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["מלאי", "inv", "bag", "i"])
    async def inventory(self, ctx: commands.Context):
        """!inventory — הצג את המלאי שלך"""
        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)

        if not user or not user["starter_selected"]:
            await ctx.send("❌ כתוב `!start` כדי להתחיל.")
            return

        inv = await db.get_inventory(discord_id)
        embed = build_inventory_embed(inv, ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="use", aliases=["השתמש", "item"])
    async def use(self, ctx: commands.Context, *, item_name: str = None):
        """
        !use <שם פריט> — השתמש בתרופה על פוקימון
        דוגמה: !use Potion
        """
        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)

        if not user or not user["starter_selected"]:
            await ctx.send("❌ כתוב `!start` כדי להתחיל.")
            return

        inv = await db.get_inventory(discord_id)
        potions = [i for i in inv if STORE_ITEMS.get(i["item_name"], {}).get("type") == "potion" and i["quantity"] > 0]

        if not potions:
            await ctx.send(
                embed=discord.Embed(
                    title="🎒 אין תרופות",
                    description="אין לך תרופות במלאי! קנה בחנות עם `!buy Potion`.",
                    color=0xFF4444
                )
            )
            return

        # אם ציין שם
        selected_potion = None
        if item_name:
            for p in potions:
                if p["item_name"].lower() == item_name.lower():
                    selected_potion = p
                    break
            if not selected_potion:
                await ctx.send(f"❌ אין לך **{item_name}** במלאי. כתוב `!inventory` לצפייה.")
                return
        else:
            # בחירה אינטראקטיבית
            selected_potion = await self._pick_potion(ctx, potions)
            if not selected_potion:
                return

        # בחירת פוקימון לריפוי
        team = await db.get_team(discord_id)
        healable = [t for t in team if t["current_hp"] < t["max_hp"] and t["current_hp"] > 0]

        if not healable:
            await ctx.send(
                embed=discord.Embed(
                    title="💚 כל הפוקימונים בריאים!",
                    description="כל הפוקימונים שלך כבר בחיים מלאים.",
                    color=0x00C851
                )
            )
            return

        target = await self._pick_pokemon(ctx, healable)
        if not target:
            return

        heal = STORE_ITEMS[selected_potion["item_name"]]["heal"]
        removed = await db.remove_item(discord_id, selected_potion["item_name"], 1)
        if not removed:
            await ctx.send("❌ שגיאה בשימוש בפריט.")
            return

        await db.heal_team_with_potion(discord_id, target["slot"], heal)

        # קבל נתוני פוקימון
        pdata = get_pokemon_by_id(target["pokemon_id"])
        new_hp = min(target["current_hp"] + heal, target["max_hp"])
        healed = new_hp - target["current_hp"]

        await ctx.send(
            embed=discord.Embed(
                title=f"💊 ריפוי!",
                description=(
                    f"**{pdata['name'] if pdata else 'פוקימון'}** רפא **{healed} HP**!\n"
                    f"HP: {new_hp}/{target['max_hp']}"
                ),
                color=0x00C851
            )
        )

    async def _pick_potion(self, ctx, potions: list) -> Optional[dict]:
        """בחירת תרופה עם ריאקציות"""
        embed = discord.Embed(title="💊 בחר תרופה:", color=0x8B4513)
        emojis = []
        for i, p in enumerate(potions[:9]):
            emoji = NUMBER_EMOJIS[i]
            embed.add_field(
                name=f"{emoji} {p['item_name']}",
                value=f"כמות: {p['quantity']} | ריפוי: {STORE_ITEMS[p['item_name']]['heal']} HP",
                inline=True
            )
            emojis.append(emoji)

        cancel = "❌"
        emojis.append(cancel)
        msg = await ctx.send(embed=embed)
        for e in emojis:
            await msg.add_reaction(e)

        def check(r, u):
            return u.id == ctx.author.id and str(r.emoji) in emojis and r.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
            return None

        await msg.delete()
        chosen = str(reaction.emoji)
        if chosen == cancel:
            return None
        idx = emojis.index(chosen)
        return potions[idx] if idx < len(potions) else None

    async def _pick_pokemon(self, ctx, team: list) -> Optional[dict]:
        """בחירת פוקימון לריפוי עם ריאקציות"""
        embed = discord.Embed(title="🐾 על איזה פוקימון להשתמש?", color=0x4169E1)
        emojis = []

        for i, entry in enumerate(team[:6]):
            pdata = get_pokemon_by_id(entry["pokemon_id"])
            emoji = NUMBER_EMOJIS[i]
            name = pdata["name"] if pdata else f"פוקימון #{entry['pokemon_id']}"
            needs = entry["max_hp"] - entry["current_hp"]
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"HP: {entry['current_hp']}/{entry['max_hp']} (חסר {needs})",
                inline=True
            )
            emojis.append(emoji)

        cancel = "❌"
        emojis.append(cancel)
        msg = await ctx.send(embed=embed)
        for e in emojis:
            await msg.add_reaction(e)

        def check(r, u):
            return u.id == ctx.author.id and str(r.emoji) in emojis and r.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
            return None

        await msg.delete()
        chosen = str(reaction.emoji)
        if chosen == cancel:
            return None
        idx = emojis.index(chosen)
        return team[idx] if idx < len(team) else None


async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
