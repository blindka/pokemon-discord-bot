"""
cogs/explore.py — מערכת אזורים וסיור | Discord UI Buttons (instant)
"""
import discord
from discord.ext import commands

from database import db
from config import ZONES, DEFAULT_ZONE


# ─────────────────────────────────────────────────────────────
# UI VIEW — בחירת אזור
# ─────────────────────────────────────────────────────────────

ZONE_STYLES = {
    "ocean":    discord.ButtonStyle.primary,
    "forest":   discord.ButtonStyle.success,
    "mountain": discord.ButtonStyle.secondary,
    "city":     discord.ButtonStyle.secondary,
    "cave":     discord.ButtonStyle.danger,
    "grass":    discord.ButtonStyle.success,
}


class ExploreView(discord.ui.View):
    """כפתורי בחירת אזור — מוצגים מיידית"""
    def __init__(self, author_id: int, zone_list: list, current_zone: str):
        super().__init__(timeout=30.0)
        self.author_id = author_id
        self.chosen_key: str | None = None

        for i, (zone_key, zone_data) in enumerate(zone_list):
            is_current = zone_key == current_zone
            label = zone_data["name"]
            if is_current:
                label += " ✓"
            style = ZONE_STYLES.get(zone_key, discord.ButtonStyle.secondary)
            btn = discord.ui.Button(
                label=label[:80],
                style=style,
                custom_id=f"zone_{zone_key}",
                row=i // 3,
                disabled=is_current,  # נוכחי — מנוטרל להדגשה
            )
            btn.callback = self._make_callback(zone_key)
            self.add_item(btn)

    def _make_callback(self, zone_key: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message(
                    "זה לא הבחירה שלך!", ephemeral=True
                )
                return
            self.chosen_key = zone_key
            await interaction.response.defer()
            self.stop()
        return callback


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

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
                "לחץ על אחד הכפתורים לשינוי האזור!\n"
                "**70%** מפוקימוני האזור · **30%** אקראי"
            ),
            color=0x00AAFF
        )

        for zone_key, zone_data in zone_list:
            is_current = "👈 **נוכחי**" if zone_key == current_zone else ""
            embed.add_field(
                name=f"{zone_data['name']} {is_current}",
                value=_zone_description(zone_key),
                inline=True
            )

        embed.set_footer(text="הכפתורים מופיעים למטה · פג תוקף בעוד 30 שניות")

        view = ExploreView(ctx.author.id, zone_list, current_zone)
        msg = await ctx.send(embed=embed, view=view)

        await view.wait()

        try:
            await msg.edit(view=None)
        except Exception:
            pass

        if view.chosen_key is None:
            return  # timeout — בשקט

        await db.set_zone(discord_id, view.chosen_key)
        zone_data = ZONES[view.chosen_key]

        confirm_embed = discord.Embed(
            title=f"✅ עברת ל{zone_data['name']}!",
            description=(
                f"כעת הקרבות שלך יתרחשו ב**{zone_data['name']}**.\n"
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
