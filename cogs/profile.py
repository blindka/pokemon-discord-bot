"""
cogs/profile.py — פרופיל שחקן ושישייה (!profile, !team, !storage)
"""
import discord
from discord.ext import commands
import json

from database import db
from utils.pokemon_utils import get_pokemon_by_id, get_sprite_url, build_hp_bar, get_type_emoji
from utils.embed_utils import build_profile_embed


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot):
        self.bot = bot

    async def _require_started(self, ctx) -> bool:
        """בדיקה שהמשתמש התחיל את המשחק"""
        user = await db.get_user(str(ctx.author.id))
        if not user or not user["starter_selected"]:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ טרם התחלת!",
                    description="כתוב `!start` כדי להתחיל.",
                    color=0xFF4444
                )
            )
            return False
        return True

    @commands.command(name="profile", aliases=["פרופיל", "me", "stats"])
    async def profile(self, ctx: commands.Context):
        """!profile — הצג את פרופיל השחקן"""
        if not await self._require_started(ctx):
            return

        discord_id = str(ctx.author.id)
        user = await db.get_user(discord_id)
        team = await db.get_team(discord_id)

        # בניית מפה של נתוני פוקימון
        pokemon_map = {}
        for entry in team:
            pdata = get_pokemon_by_id(entry["pokemon_id"])
            if pdata:
                pokemon_map[entry["pokemon_id"]] = pdata

        embed = build_profile_embed(user, team, pokemon_map)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="team", aliases=["שישייה", "t"])
    async def team(self, ctx: commands.Context):
        """!team — הצג את השישייה המפורטת"""
        if not await self._require_started(ctx):
            return

        discord_id = str(ctx.author.id)
        team = await db.get_team(discord_id)

        if not team:
            await ctx.send(
                embed=discord.Embed(
                    title="🐾 הצוות ריק",
                    description="אין לך פוקימונים! כתוב `!battle` כדי ללכוד פוקימונים.",
                    color=0xFF4444
                )
            )
            return

        embed = discord.Embed(
            title=f"🐾 השישייה של {ctx.author.display_name}",
            color=0x4169E1
        )

        for i, entry in enumerate(team):
            pdata = get_pokemon_by_id(entry["pokemon_id"])
            if not pdata:
                continue

            type_emoji = get_type_emoji(pdata["type"][0])
            hp_bar = build_hp_bar(entry["current_hp"], entry["max_hp"], length=8)
            status = "✅" if entry["current_hp"] > 0 else "💀"
            types_str = "/".join(pdata["type"])

            embed.add_field(
                name=f"Slot {i+1} {status} — {type_emoji} {pdata['name']}",
                value=(
                    f"**רמה:** {entry['level']} | **סוג:** {types_str}\n"
                    f"**HP:** {hp_bar}\n"
                    f"⚔️ {pdata['attack']} | 🛡️ {pdata['defense']} | 💨 {pdata['speed']}\n"
                    f"**מהלכים:** {', '.join(pdata.get('moves', [])[:4])}"
                ),
                inline=False
            )

        sprite_id = team[0]["pokemon_id"]
        embed.set_thumbnail(url=get_sprite_url(sprite_id))
        await ctx.send(embed=embed)

    @commands.command(name="storage", aliases=["אחסון", "box"])
    async def storage(self, ctx: commands.Context):
        """!storage — הצג את אחסון הפוקימונים"""
        if not await self._require_started(ctx):
            return

        discord_id = str(ctx.author.id)
        stored = await db.get_storage(discord_id)

        embed = discord.Embed(
            title=f"📦 אחסון של {ctx.author.display_name}",
            color=0x9B59B6
        )

        if not stored:
            embed.description = "האחסון ריק. לכוד פוקימונים קודם!"
            await ctx.send(embed=embed)
            return

        # קבץ 3 בשורה
        lines = []
        for entry in stored:
            pdata = get_pokemon_by_id(entry["pokemon_id"])
            if pdata:
                type_emoji = get_type_emoji(pdata["type"][0])
                lines.append(f"{type_emoji} **{pdata['name']}** Lv.{entry['level']}")

        # חלק ל-chunks של 10
        chunk_size = 10
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i+chunk_size]
            embed.add_field(
                name=f"פוקימונים {i+1}–{i+len(chunk)}",
                value="\n".join(chunk),
                inline=True
            )

        embed.set_footer(text=f"סה\"כ: {len(stored)} פוקימונים באחסון")
        await ctx.send(embed=embed)

    @commands.command(name="pokedex", aliases=["פוקידקס", "dex", "pokemon"])
    async def pokedex(self, ctx: commands.Context, *, name_or_id: str = None):
        """!pokedex <שם/מספר> — מידע על פוקימון"""
        if not name_or_id:
            await ctx.send(
                embed=discord.Embed(
                    title="📖 פוקידקס",
                    description="השימוש: `!pokedex <שם פוקימון>` או `!pokedex <מספר>`\n\nדוגמה: `!pokedex Pikachu` או `!pokedex 25`",
                    color=0xFFD700
                )
            )
            return

        from utils.pokemon_utils import get_pokemon_by_name, get_pokemon_by_id, get_all_pokemon

        # ניסיון לפי מספר
        pdata = None
        if name_or_id.isdigit():
            pdata = get_pokemon_by_id(int(name_or_id))
        else:
            pdata = get_pokemon_by_name(name_or_id)

        if not pdata:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ פוקימון לא נמצא",
                    description=f"לא מצאתי פוקימון בשם **{name_or_id}**.",
                    color=0xFF4444
                )
            )
            return

        from utils.embed_utils import build_pokemon_embed
        from config import TYPE_COLORS
        embed = build_pokemon_embed(pdata)

        # # הצג אם בפוקידקס של המשתמש
        user = await db.get_user(str(ctx.author.id))
        if user:
            seen_ids = json.loads(user.get("pokedex_ids", "[]"))
            seen_str = "✅ ראית/לכדת" if pdata["id"] in seen_ids else "❌ לא ראית עדיין"
            embed.add_field(name="סטטוס בפוקידקס", value=seen_str, inline=True)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
