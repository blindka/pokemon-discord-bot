"""
cogs/starter.py — בחירת פוקימון ראשוני (!start) | Discord UI Buttons
"""
import discord
from discord.ext import commands

from database import db
from utils.pokemon_utils import get_pokemon_by_id, get_starters, get_sprite_url
from utils.embed_utils import build_starter_embed, build_pokemon_embed
from config import STARTING_ITEMS
from utils.battle_utils import get_move_info
from utils.log_utils import send_log


# ─────────────────────────────────────────────────────────────
# UI VIEW — בחירת פוקימון התחלתי
# ─────────────────────────────────────────────────────────────

class StarterView(discord.ui.View):
    """כפתורי בחירת פוקימון התחלתי — מוצגים מיידית"""
    def __init__(self, author_id: int, starters: list):
        super().__init__(timeout=60.0)
        self.author_id = author_id
        self.chosen_index: int | None = None
        self._starters = starters

        STARTER_EMOJIS = ["🌿", "🔥", "💧"]
        STARTER_STYLES = [
            discord.ButtonStyle.success,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.primary,
        ]

        for i, pokemon in enumerate(starters):
            emoji = STARTER_EMOJIS[i] if i < len(STARTER_EMOJIS) else "⭐"
            style = STARTER_STYLES[i] if i < len(STARTER_STYLES) else discord.ButtonStyle.secondary
            types = " / ".join(pokemon.get("type", ["Normal"]))
            label = f"{emoji} {pokemon['name']}  [{types}]"
            btn = discord.ui.Button(
                label=label[:80],
                style=style,
                custom_id=f"starter_{i}",
                row=0,
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message(
                    "זה לא הבחירה שלך!", ephemeral=True
                )
                return
            self.chosen_index = index
            await interaction.response.defer()
            self.stop()
        return callback


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class StarterCog(commands.Cog, name="Starter"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="start", aliases=["התחל", "begin"])
    async def start(self, ctx: commands.Context):
        """!start — מתחיל את המשחק ובוחר פוקימון התחלתי"""
        discord_id = str(ctx.author.id)
        username = str(ctx.author.name)

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

        starters = get_starters()

        embeds = []
        main_embed = discord.Embed(
            title="🌟 ברוך הבא לעולם הפוקימונים!",
            description=(
                "בחר את הפוקימון ההתחלתי שלך!\n"
                "לחץ על אחד הכפתורים למטה:"
            ),
            color=0xFFD700
        )
        embeds.append(main_embed)

        STARTER_COLORS = [0x78C850, 0xF08030, 0x6890F0]
        STARTER_EMOJIS = ["🌿", "🔥", "💧"]
        for i, pokemon in enumerate(starters):
            emoji = STARTER_EMOJIS[i] if i < len(STARTER_EMOJIS) else "⭐"
            color = STARTER_COLORS[i] if i < len(STARTER_COLORS) else 0xFFD700
            types_str = " / ".join(pokemon.get("type", ["Normal"]))
            moves = pokemon.get("moves", [])[:4]
            moves_str = " · ".join(moves) if moves else "Tackle"
            
            p_embed = discord.Embed(
                title=f"{emoji} {pokemon['name']}",
                description=(
                    f"**סוג:** {types_str}\n"
                    f"**HP:** {pokemon.get('hp', '?')} | "
                    f"**ATK:** {pokemon.get('attack', '?')} | "
                    f"**SPD:** {pokemon.get('speed', '?')}\n"
                    f"**מהלכים:** {moves_str}"
                ),
                color=color
            )
            p_embed.set_thumbnail(url=get_sprite_url(pokemon['id']))
            embeds.append(p_embed)

        embeds[-1].set_footer(text="לחץ על הכפתור לבחירה · הבחירה תפוג בעוד 60 שניות")

        view = StarterView(ctx.author.id, starters)
        msg = await ctx.send(embeds=embeds, view=view)

        await view.wait()

        # נטרל כפתורים אחרי בחירה/פג זמן
        try:
            await msg.edit(view=None)
        except Exception:
            pass

        if view.chosen_index is None:
            await ctx.send(embed=discord.Embed(
                title="⏰ פג הזמן!",
                description="לא בחרת פוקימון בתוך 60 שניות. כתוב `!start` שוב.",
                color=0xFF4444
            ))
            return

        chosen_pokemon = starters[view.chosen_index]
        if not chosen_pokemon:
            await ctx.send("❌ שגיאה במציאת הפוקימון. נסה שוב.")
            return

        # שמירה למסד הנתונים
        await db.add_to_team(discord_id, chosen_pokemon["id"], chosen_pokemon["hp"], level=5)
        await db.set_starter_selected(discord_id)
        await db.add_to_pokedex(discord_id, chosen_pokemon["id"])

        for item_name, qty in STARTING_ITEMS.items():
            await db.add_item(discord_id, item_name, qty)

        STARTER_EMOJIS = ["🌿", "🔥", "💧"]
        emoji = STARTER_EMOJIS[view.chosen_index] if view.chosen_index < 3 else "⭐"

        success_embed = discord.Embed(
            title=f"🎉 {emoji} בחרת את {chosen_pokemon['name']}!",
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
        await ctx.send(embed=success_embed)

        # ── Log ──
        STARTER_EMOJIS = ["🌿", "🔥", "💧"]
        s_emoji = STARTER_EMOJIS[view.chosen_index] if view.chosen_index < 3 else "⭐"
        await send_log(
            ctx.bot,
            category="player",
            title="שחקן חדש הצטרף!",
            description=f"בחר פוקימון ראשוני: {s_emoji} **{chosen_pokemon['name']}**",
            fields=[
                ("💰 Silver התחלתי", "1,000", True),
                ("🔴 Poké Balls", "5", True),
            ],
            user=ctx.author,
        )


async def setup(bot):
    await bot.add_cog(StarterCog(bot))
