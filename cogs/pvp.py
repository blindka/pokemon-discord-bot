"""
cogs/pvp.py — מערכת קרבות PvP בין שחקנים | Discord UI Buttons (instant)
"""
import discord
from discord.ext import commands
import asyncio
import random

from database import db
from utils.pokemon_utils import (
    get_pokemon_by_id, build_hp_bar, get_sprite_url, format_pokemon_types
)
from utils.battle_utils import (
    calculate_damage, is_critical_hit, get_move_info, format_battle_log
)
from config import BATTLE_TIMEOUT
from utils.log_utils import send_log


# ─────────────────────────────────────────────────────────────
# UI VIEWS
# ─────────────────────────────────────────────────────────────

class PvPInviteView(discord.ui.View):
    """כפתורי קבלה/דחייה של אתגר PvP"""
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60.0)
        self.challenger = challenger
        self.opponent = opponent
        self.accepted: bool | None = None

    @discord.ui.button(label="✅ קבל את האתגר!", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("זה לא האתגר שלך!", ephemeral=True)
            return
        self.accepted = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ דחה", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("זה לא האתגר שלך!", ephemeral=True)
            return
        self.accepted = False
        await interaction.response.defer()
        self.stop()


class PvPMoveView(discord.ui.View):
    """כפתורי בחירת מהלך ב-PvP"""
    def __init__(self, player: discord.Member, moves: list, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.player = player
        self.chosen_move: str | None = None

        MOVE_STYLES = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.success,
        ]

        for i, move_name in enumerate(moves[:4]):
            info = get_move_info(move_name)
            power_str = f" ({info['power']})" if info.get("power", 0) > 0 else " (סטטוס)"
            label = f"{info.get('emoji', '💥')} {move_name}{power_str}"
            style = MOVE_STYLES[i] if i < len(MOVE_STYLES) else discord.ButtonStyle.secondary
            btn = discord.ui.Button(
                label=label[:80],
                style=style,
                custom_id=f"pvp_move_{i}",
                row=i // 2,
            )
            btn.callback = self._make_callback(move_name)
            self.add_item(btn)

    def _make_callback(self, move_name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.player.id:
                await interaction.response.send_message(
                    "זה לא התור שלך!", ephemeral=True
                )
                return
            self.chosen_move = move_name
            await interaction.response.defer()
            self.stop()
        return callback


# ─────────────────────────────────────────────────────────────
# COG
# ─────────────────────────────────────────────────────────────

class PvPCog(commands.Cog, name="PvP"):
    def __init__(self, bot):
        self.bot = bot
        self.active_challenges: set[str] = set()

    @commands.command(name="duel", aliases=["אתגר", "pvp", "challenge", "d"])
    async def challenge(self, ctx: commands.Context, opponent: discord.Member = None):
        """!duel @user — אתגר שחקן אחר לקרב PvP"""
        if not opponent:
            await ctx.send(embed=discord.Embed(
                title="❌ ציין יריב!",
                description="דוגמה: `!duel @שם`",
                color=0xFF4444
            ))
            return

        if opponent.bot:
            await ctx.send("❌ אי אפשר לאתגר בוט!")
            return

        if opponent.id == ctx.author.id:
            await ctx.send("❌ אי אפשר לאתגר את עצמך!")
            return

        p1_id = str(ctx.author.id)
        p2_id = str(opponent.id)

        p1_user = await db.get_user(p1_id)
        p2_user = await db.get_user(p2_id)

        if not p1_user or not p1_user["starter_selected"]:
            await ctx.send("❌ אתה עוד לא רשום! כתוב `!start`.")
            return
        if not p2_user or not p2_user["starter_selected"]:
            await ctx.send(f"❌ {opponent.display_name} עוד לא רשום!")
            return

        if p1_id in self.active_challenges or p2_id in self.active_challenges:
            await ctx.send("⚔️ אחד מכם כבר באתגר פעיל!")
            return

        # שלח הזמנה עם כפתורים
        invite_embed = discord.Embed(
            title="⚔️ אתגר PvP!",
            description=(
                f"**{ctx.author.display_name}** מאתגר את **{opponent.display_name}** לקרב!\n\n"
                f"{opponent.mention}, לחץ על הכפתור לקבל או לדחות:"
            ),
            color=0xFF6600
        )
        invite_embed.set_footer(text="האתגר יפוג בעוד 60 שניות")

        invite_view = PvPInviteView(ctx.author, opponent)
        invite_msg = await ctx.send(embed=invite_embed, view=invite_view)

        await invite_view.wait()

        try:
            await invite_msg.edit(view=None)
        except Exception:
            pass

        if invite_view.accepted is None:
            await ctx.send(f"⏰ {opponent.display_name} לא הגיב בזמן.")
            return

        if not invite_view.accepted:
            await ctx.send(f"❌ {opponent.display_name} דחה את האתגר.")
            return

        # הכנת פוקימונים
        p1_team = await db.get_team(p1_id)
        p2_team = await db.get_team(p2_id)

        p1_alive = [t for t in p1_team if t["current_hp"] > 0]
        p2_alive = [t for t in p2_team if t["current_hp"] > 0]

        if not p1_alive:
            await ctx.send(f"❌ כל הפוקימונים של {ctx.author.display_name} מחוסרי הכרה!")
            return
        if not p2_alive:
            await ctx.send(f"❌ כל הפוקימונים של {opponent.display_name} מחוסרי הכרה!")
            return

        p1_entry = p1_alive[0]
        p2_entry = p2_alive[0]
        p1_pokemon = get_pokemon_by_id(p1_entry["pokemon_id"])
        p2_pokemon = get_pokemon_by_id(p2_entry["pokemon_id"])

        if not p1_pokemon or not p2_pokemon:
            await ctx.send("❌ שגיאה בטעינת פוקימונים.")
            return

        self.active_challenges.add(p1_id)
        self.active_challenges.add(p2_id)

        try:
            await self._pvp_loop(
                ctx, ctx.author, opponent,
                p1_pokemon, p1_entry,
                p2_pokemon, p2_entry
            )
        finally:
            self.active_challenges.discard(p1_id)
            self.active_challenges.discard(p2_id)

    async def _pvp_loop(
        self, ctx,
        user1: discord.Member, user2: discord.Member,
        p1_pokemon: dict, p1_entry: dict,
        p2_pokemon: dict, p2_entry: dict
    ):
        """לולאת PvP — כפתורים מיידיים לכל תור"""
        battle_log = [f"⚔️ **{user1.display_name}** vs **{user2.display_name}**!"]
        turn = 1
        pvp_msg = None

        while True:
            # ─── תור שחקן 1 ───
            p1_moves = p1_pokemon.get("moves", ["Tackle"])[:4]
            embed = self._build_pvp_embed(
                user1, user2, p1_pokemon, p1_entry, p2_pokemon, p2_entry,
                battle_log, turn, current_turn_user=user1, moves=p1_moves
            )
            view1 = PvPMoveView(user1, p1_moves, timeout=float(BATTLE_TIMEOUT))

            if pvp_msg is None:
                pvp_msg = await ctx.send(embed=embed, view=view1)
            else:
                await pvp_msg.edit(embed=embed, view=view1)

            await view1.wait()
            try:
                await pvp_msg.edit(view=None)
            except Exception:
                pass

            if view1.chosen_move is None:
                await ctx.send(f"⏰ {user1.display_name} לא בחר מהלך — הפסיד!")
                return
            p1_move = view1.chosen_move

            # ─── תור שחקן 2 ───
            p2_moves = p2_pokemon.get("moves", ["Tackle"])[:4]
            embed2 = self._build_pvp_embed(
                user1, user2, p1_pokemon, p1_entry, p2_pokemon, p2_entry,
                battle_log, turn, current_turn_user=user2, moves=p2_moves
            )
            view2 = PvPMoveView(user2, p2_moves, timeout=float(BATTLE_TIMEOUT))

            await pvp_msg.edit(embed=embed2, view=view2)
            await view2.wait()
            try:
                await pvp_msg.edit(view=None)
            except Exception:
                pass

            if view2.chosen_move is None:
                await ctx.send(f"⏰ {user2.display_name} לא בחר מהלך — הפסיד!")
                return
            p2_move = view2.chosen_move

            # ─── חישוב: מי מהיר תוקף ראשון ───
            p1_speed = p1_pokemon.get("speed", 50)
            p2_speed = p2_pokemon.get("speed", 50)
            if p1_speed >= p2_speed:
                order = [
                    (p1_pokemon, p1_entry, p1_move, p2_pokemon, p2_entry, user1, user2),
                    (p2_pokemon, p2_entry, p2_move, p1_pokemon, p1_entry, user2, user1),
                ]
            else:
                order = [
                    (p2_pokemon, p2_entry, p2_move, p1_pokemon, p1_entry, user2, user1),
                    (p1_pokemon, p1_entry, p1_move, p2_pokemon, p2_entry, user1, user2),
                ]

            for atk_poke, atk_entry, move, def_poke, def_entry, atk_user, def_user in order:
                self._resolve_attack(atk_poke, atk_entry, move, def_poke, def_entry, battle_log)
                if def_entry["current_hp"] <= 0:
                    final_embed = self._build_pvp_embed(
                        user1, user2, p1_pokemon, p1_entry, p2_pokemon, p2_entry,
                        battle_log, turn
                    )
                    await pvp_msg.edit(embed=final_embed, view=None)
                    await ctx.send(embed=discord.Embed(
                        title=f"🏆 {atk_user.display_name} ניצח!",
                        description=f"**{def_poke['name']}** של {def_user.display_name} חוסר הכרה!",
                        color=0x00FF00
                    ))

                    # ── Log PvP ──
                    await send_log(
                        ctx.bot,
                        category="pvp",
                        title="קרב PvP הסתיים!",
                        description=f"ניצחון: **{atk_user.display_name}** נגד **{def_user.display_name}**",
                        fields=[
                            ("🟥 מנצח", f"{atk_poke['name']} Lv.{atk_entry.get('level',5)}", True),
                            ("🟦 פסדן", f"{def_poke['name']} Lv.{def_entry.get('level',5)}", True),
                            ("🔄 תור", str(turn), True),
                        ],
                        user=atk_user,
                    )

                    return

            turn += 1

    def _resolve_attack(self, atk_poke, atk_entry, move_name, def_poke, def_entry, battle_log):
        """חישוב נזק"""
        move_info = get_move_info(move_name)
        emoji = move_info.get("emoji", "💥")

        if move_info.get("status", False) or move_info.get("power", 0) == 0:
            battle_log.append(f"{atk_poke['name']} ← {emoji} **{move_name}**!")
            return

        damage = calculate_damage(atk_poke, def_poke, move_name)
        crit = is_critical_hit(atk_poke.get("speed", 50))
        if crit:
            damage = int(damage * 1.5)
        def_entry["current_hp"] = max(0, def_entry["current_hp"] - damage)
        crit_text = " **(קריטי!)**" if crit else ""
        battle_log.append(
            f"{atk_poke['name']} ← {emoji} **{move_name}** → **{damage}** נזק{crit_text}!"
        )

    def _build_pvp_embed(
        self, user1, user2,
        p1_pokemon, p1_entry, p2_pokemon, p2_entry,
        battle_log, turn,
        current_turn_user=None, moves=None
    ) -> discord.Embed:
        """Embed ל-PvP עם רשימת מהלכים"""
        embed = discord.Embed(
            title="⚔️ קרב PvP!",
            color=0xFF6600
        )

        p1_hp_bar = build_hp_bar(p1_entry["current_hp"], p1_entry["max_hp"])
        p1_types = format_pokemon_types(p1_pokemon.get("type", ["Normal"]))
        embed.add_field(
            name=f"🔴 {user1.display_name} — {p1_pokemon['name']} Lv.{p1_entry.get('level', 5)}",
            value=f"{p1_types}\n{p1_hp_bar}",
            inline=False
        )

        embed.add_field(name="⎯⎯⎯ VS ⎯⎯⎯", value="\u200b", inline=False)

        p2_hp_bar = build_hp_bar(p2_entry["current_hp"], p2_entry["max_hp"])
        p2_types = format_pokemon_types(p2_pokemon.get("type", ["Normal"]))
        embed.add_field(
            name=f"🔵 {user2.display_name} — {p2_pokemon['name']} Lv.{p2_entry.get('level', 5)}",
            value=f"{p2_types}\n{p2_hp_bar}",
            inline=False
        )

        if current_turn_user:
            embed.add_field(
                name=f"🎯 תור {current_turn_user.display_name}",
                value="בחר מהלך מהכפתורים למטה:",
                inline=False
            )

        if battle_log:
            log_text = format_battle_log(battle_log)
            if len(log_text) > 1024:
                log_text = log_text[-1020:] + "..."
            embed.add_field(name="📜 יומן", value=log_text, inline=False)

        embed.set_footer(text=f"תור {turn}")
        return embed


async def setup(bot):
    await bot.add_cog(PvPCog(bot))
