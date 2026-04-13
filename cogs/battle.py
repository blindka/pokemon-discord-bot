"""
cogs/battle.py — מערכת קרבות מלאה עם Discord UI Buttons (instant interaction)
"""
import discord
from discord.ext import commands
import asyncio
import random

from database import db
from utils.pokemon_utils import (
    get_pokemon_by_id, get_wild_pokemon_for_zone,
    build_hp_bar, get_sprite_url, calculate_catch_rate, get_rarity
)
from utils.battle_utils import (
    calculate_damage, calculate_wild_damage,
    is_critical_hit, get_move_info, format_battle_log
)
from utils.embed_utils import build_battle_moves_embed, build_catch_embed
from config import (
    BATTLE_TIMEOUT, NUMBER_EMOJIS,
    SILVER_REWARDS,
    STORE_ITEMS
)
from utils.log_utils import send_log


# ─────────────────────────────────────────────────────────────
# UI VIEWS
# ─────────────────────────────────────────────────────────────

class BattleView(discord.ui.View):
    """
    כפתורי פעולה בקרב.
    כל הכפתורים מוצגים בו-זמנית עם ה-embed — ללא המתנה.
    """
    def __init__(self, author_id: int, moves: list, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.action_index: int | None = None
        self._moves = moves

        num_moves = min(len(moves), 4)

        # Move buttons (row 0 + 1)
        for i, move_name in enumerate(moves[:4]):
            info = get_move_info(move_name)
            label = f"{info['emoji']} {move_name}"
            btn = discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"move_{i}",
                row=i // 2,          # row 0 = moves 0&1, row 1 = moves 2&3
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

        # Utility buttons (row 2)
        inv_btn = discord.ui.Button(label="🎒 תיק חפצים", style=discord.ButtonStyle.secondary,
                                    custom_id="inv", row=2)
        inv_btn.callback = self._make_callback(num_moves)
        self.add_item(inv_btn)

        sw_btn = discord.ui.Button(label="🔄 החלף", style=discord.ButtonStyle.secondary,
                                   custom_id="sw", row=2)
        sw_btn.callback = self._make_callback(num_moves + 1)
        self.add_item(sw_btn)

        run_btn = discord.ui.Button(label="🏃 ברח", style=discord.ButtonStyle.danger,
                                    custom_id="run", row=2)
        run_btn.callback = self._make_callback(num_moves + 2)
        self.add_item(run_btn)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
                return
            self.action_index = index
            await interaction.response.defer()
            self.stop()
        return callback


class SwitchView(discord.ui.View):
    """כפתורי בחירת פוקימון להחלפה"""
    def __init__(self, author_id: int, entries: list, include_cancel: bool = True):
        super().__init__(timeout=30.0)
        self.author_id = author_id
        self.chosen_index: int | None = None
        self._entries = entries

        for i, entry in enumerate(entries[:6]):
            poke = get_pokemon_by_id(entry["pokemon_id"])
            if not poke:
                continue
            hp_pct = int((entry["current_hp"] / entry["max_hp"]) * 100)
            label = f"{poke['name']} Lv.{entry['level']} ({hp_pct}% HP)"
            btn = discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.success,
                custom_id=f"sw_{i}",
                row=i // 3,
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

        if include_cancel:
            cancel = discord.ui.Button(label="❌ ביטול", style=discord.ButtonStyle.danger,
                                       custom_id="cancel", row=2)
            cancel.callback = self._cancel_callback
            self.add_item(cancel)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
                return
            self.chosen_index = index
            await interaction.response.defer()
            self.stop()
        return callback

    async def _cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
            return
        self.chosen_index = None
        await interaction.response.defer()
        self.stop()


class InventoryView(discord.ui.View):
    """כפתורי בחירת פריט מהמלאי"""
    def __init__(self, author_id: int, items: list):
        super().__init__(timeout=30.0)
        self.author_id = author_id
        self.chosen_index: int | None = None
        self._items = items

        for i, item in enumerate(items[:9]):
            info = STORE_ITEMS.get(item["item_name"], {})
            emoji = info.get("emoji", "📦")
            label = f"{emoji} {item['item_name']} ×{item['quantity']}"
            btn = discord.ui.Button(
                label=label[:80],
                style=discord.ButtonStyle.primary,
                custom_id=f"item_{i}",
                row=i // 3,
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

        cancel = discord.ui.Button(label="❌ ביטול", style=discord.ButtonStyle.danger,
                                   custom_id="cancel", row=3)
        cancel.callback = self._cancel_callback
        self.add_item(cancel)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
                return
            self.chosen_index = index
            await interaction.response.defer()
            self.stop()
        return callback

    async def _cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
            return
        self.chosen_index = None
        await interaction.response.defer()
        self.stop()


class EvolutionView(discord.ui.View):
    """כפתורי אישור/ביטול התפתחות"""
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("זה לא הקרב שלך!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Evolve!", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="❌ Keep", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


# ─────────────────────────────────────────────────────────────
# BATTLE COG
# ─────────────────────────────────────────────────────────────

class BattleCog(commands.Cog, name="Battle"):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles: set[str] = set()

    @commands.command(name="battle", aliases=["קרב", "fight", "b"])
    async def battle(self, ctx: commands.Context):
        """!battle — מתחיל קרב עם פוקימון פראי בהתאם לאזור"""
        discord_id = str(ctx.author.id)

        user = await db.get_user(discord_id)
        if not user or not user["starter_selected"]:
            await ctx.send(embed=discord.Embed(
                title="❌ טרם התחלת!",
                description="כתוב `!start` כדי לבחור פוקימון התחלתי.",
                color=0xFF4444
            ))
            return

        if discord_id in self.active_battles:
            await ctx.send("⚔️ אתה כבר בתוך קרב!")
            return

        team = await db.get_team(discord_id)
        alive_team = [t for t in team if t["current_hp"] > 0]

        if not alive_team:
            await ctx.send(embed=discord.Embed(
                title="💀 כל הפוקימונים שלך מחוסרי הכרה!",
                description="כתוב `!heal` כדי לרפא.",
                color=0xFF4444
            ))
            return

        player_entry = alive_team[0]
        player_pokemon = get_pokemon_by_id(player_entry["pokemon_id"])
        if not player_pokemon:
            await ctx.send("❌ שגיאה בטעינת פוקימונים.")
            return

        zone = await db.get_zone(discord_id)
        wild = get_wild_pokemon_for_zone(zone, player_entry.get("level", 5))

        self.active_battles.add(discord_id)
        await db.increment_battles(discord_id)

        from config import ZONES, DEFAULT_ZONE
        zone_name = ZONES.get(zone, ZONES.get(DEFAULT_ZONE))["name"]

        battle_log = [
            f"{zone_name} | 🌿 **{wild['name']}** Lv.{wild['level']} הופיע!"
        ]
        turn = 1

        try:
            await self._battle_loop(
                ctx, discord_id, player_pokemon, player_entry, wild, battle_log, turn
            )
        finally:
            self.active_battles.discard(discord_id)

    async def _battle_loop(
        self, ctx, discord_id: str,
        player_pokemon: dict, player_entry: dict,
        wild: dict, battle_log: list, turn: int
    ):
        """לולאת הקרב — כפתורים מופיעים מיד עם ה-embed"""
        battle_msg = None

        while True:
            moves = player_pokemon.get("moves", [])
            num_moves = min(len(moves), 4)

            embed, _ = build_battle_moves_embed(
                player_pokemon, wild, player_entry, battle_log, turn
            )

            # Build button view — sent WITH the embed, appear instantly
            view = BattleView(ctx.author.id, moves, timeout=float(BATTLE_TIMEOUT))

            if battle_msg is None:
                battle_msg = await ctx.send(embed=embed, view=view)
            else:
                await battle_msg.edit(embed=embed, view=view)

            # Wait for button press
            await view.wait()

            # Disable buttons immediately after interaction
            try:
                await battle_msg.edit(view=None)
            except Exception:
                pass

            if view.action_index is None:
                # Timeout
                await ctx.send(embed=discord.Embed(
                    title="⏰ פג הזמן!",
                    description=f"הקרב נגד {wild['name']} הסתיים.",
                    color=0xFF4444
                ))
                return

            action_index = view.action_index

            # --- MOVE ---
            if action_index < num_moves:
                move_name = moves[action_index]
                move_info = get_move_info(move_name)
                move_emoji = move_info.get("emoji", "💥")

                if move_info.get("status", False) or move_info.get("power", 0) == 0:
                    battle_log.append(f"{player_pokemon['name']} השתמש ב-{move_emoji} **{move_name}**!")
                else:
                    damage = calculate_damage(player_pokemon, wild, move_name)
                    crit = is_critical_hit(player_pokemon.get("speed", 50))
                    if crit:
                        damage = int(damage * 1.5)
                    wild["current_hp"] = max(0, wild["current_hp"] - damage)
                    crit_text = " **(קריטי!)**" if crit else ""
                    battle_log.append(
                        f"{player_pokemon['name']} ← {move_emoji} **{move_name}**! "
                        f"**{damage}** נזק{crit_text}!"
                    )

                if wild["current_hp"] <= 0:
                    await self._handle_victory(ctx, discord_id, player_entry, wild, battle_msg)
                    return

                await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)

                if player_entry["current_hp"] <= 0:
                    switched = await self._handle_faint(ctx, discord_id, wild, player_pokemon, battle_log)
                    if switched is None:
                        return
                    player_pokemon, player_entry = switched

            # --- מלאי ---
            elif action_index == num_moves:
                inv = await db.get_inventory(discord_id)
                usable = [i for i in inv if i["item_name"] in
                          ["Poké Ball", "Great Ball", "Ultra Ball",
                           "Potion", "Super Potion", "Hyper Potion"]]

                if not usable:
                    battle_log.append("🎒 תיק החפצים ריק!")
                else:
                    item_result = await self._show_inventory_menu(
                        ctx, discord_id, usable, wild, player_pokemon, player_entry, battle_log
                    )
                    if item_result == "caught":
                        return
                    elif item_result == "used_potion":
                        team = await db.get_team(discord_id)
                        for t in team:
                            if t["slot"] == player_entry["slot"]:
                                player_entry = t
                                break

            # --- החלפת פוקימון ---
            elif action_index == num_moves + 1:
                switched = await self._show_switch_menu(ctx, discord_id, player_entry, battle_log)
                if switched:
                    player_pokemon, player_entry = switched
                    battle_log.append(f"🔄 קדימה, **{player_pokemon['name']}**!")
                    await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                    if player_entry["current_hp"] <= 0:
                        sw = await self._handle_faint(ctx, discord_id, wild, player_pokemon, battle_log)
                        if sw is None:
                            return
                        player_pokemon, player_entry = sw
                else:
                    battle_log.append("❌ ביטלת את ההחלפה.")

            # --- ברח ---
            elif action_index == num_moves + 2:
                if random.random() < 0.5:
                    await ctx.send(embed=discord.Embed(
                        title="🏃 ברחת!",
                        description=f"ברחת מהקרב נגד **{wild['name']}**.",
                        color=0xFFA500
                    ))
                    return
                else:
                    battle_log.append("🏃 לא הצלחת לברוח!")
                    await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                    if player_entry["current_hp"] <= 0:
                        switched = await self._handle_faint(ctx, discord_id, wild, player_pokemon, battle_log)
                        if switched is None:
                            return
                        player_pokemon, player_entry = switched

            turn += 1

    async def _handle_victory(self, ctx, discord_id, player_entry, wild, battle_msg):
        """Victory — rarity-based silver, XP, level up, evolution prompt"""
        rarity = get_rarity(wild["id"])
        min_s, max_s = SILVER_REWARDS.get(rarity, (1, 3))
        silver_reward = random.randint(min_s, max_s)
        await db.update_silver(discord_id, silver_reward)

        base_exp = wild.get("baseExp", 100)
        wild_level = wild.get("level", 5)
        xp_gained = max(int(base_exp * wild_level / 7), 10)

        xp_result = await db.give_exp_and_check_levelup(
            discord_id, player_entry["slot"], xp_gained
        )

        rarity_emoji = {"common": "⚪", "uncommon": "🟢", "rare": "🔵",
                        "very_rare": "🟣", "legendary": "🟡"}.get(rarity, "⚪")
        desc = (
            f"✅ **{wild['name']}** הובס!\n"
            f"{rarity_emoji} *{rarity.replace('_', ' ').title()}*\n"
            f"💰 **{silver_reward} Silver**\n"
            f"⭐ **{xp_gained} XP**"
        )

        if xp_result["leveled_up"]:
            desc += f"\n\n🎉 **Level Up! רמה {xp_result['new_level']}!**"

        victory_embed = discord.Embed(title="🏆 ניצחת!", description=desc, color=0x00FF00)
        victory_embed.set_thumbnail(url=get_sprite_url(wild["id"]))
        await ctx.send(embed=victory_embed)

        # ── Log ──
        await send_log(
            ctx.bot,
            category="battle",
            title="ניצחון בקרב פראי!",
            fields=[
                ("🐾 פוקימון", f"{wild['name']} Lv.{wild.get('level',5)} {rarity_emoji}", True),
                ("💰 Silver", f"+{silver_reward}", True),
                ("⭐ XP", f"+{xp_gained}", True),
            ],
            user=ctx.author,
        )

        # --- Evolution prompt ---
        if xp_result.get("can_evolve") and xp_result.get("would_evolve_to"):
            old_poke = get_pokemon_by_id(xp_result["old_pokemon_id"])
            new_poke = get_pokemon_by_id(xp_result["would_evolve_to"])
            old_name = old_poke["name"] if old_poke else "?"
            new_name = new_poke["name"] if new_poke else "?"

            evo_embed = discord.Embed(
                title=f"✨ {old_name} רוצה להתפתח!",
                description=(
                    f"**{old_name}** הגיע לרמה להתפתח ל-**{new_name}**!\n"
                    f"האם אתה רוצה להתפתח עכשיו?"
                ),
                color=0xFFD700
            )
            if old_poke:
                evo_embed.set_thumbnail(url=get_sprite_url(old_poke["id"]))
            if new_poke:
                evo_embed.set_image(url=get_sprite_url(new_poke["id"]))

            view = EvolutionView(ctx.author.id)
            evo_msg = await ctx.send(embed=evo_embed, view=view)
            await view.wait()

            try:
                await evo_msg.edit(view=None)
            except Exception:
                pass

            if view.confirmed:
                await db.apply_evolution(
                    discord_id, player_entry["slot"], xp_result["would_evolve_to"]
                )
                confirm_embed = discord.Embed(
                    title=f"🌟✨ {old_name} התפתח ל-{new_name}!",
                    color=0xFFD700
                )
                if new_poke:
                    confirm_embed.set_image(url=get_sprite_url(new_poke["id"]))
                await ctx.send(embed=confirm_embed)
            else:
                await ctx.send(f"🚫 {old_name} לא התפתח. אפשר להתפתח אחרכך!")

    async def _wild_attack(self, ctx, discord_id, player_pokemon, player_entry, wild, battle_log):
        """תקיפה של הפוקימון הפראי"""
        wild_moves = wild.get("moves", ["Tackle"])
        move_name = random.choice(wild_moves)
        move_info = get_move_info(move_name)

        if move_info.get("status", False) or move_info.get("power", 0) == 0:
            battle_log.append(f"🌿 {wild['name']} ← {move_info.get('emoji','')} **{move_name}**!")
        else:
            damage = calculate_wild_damage(wild, player_pokemon)
            new_hp = max(0, player_entry["current_hp"] - damage)
            player_entry["current_hp"] = new_hp
            await db.update_team_pokemon_hp(discord_id, player_entry["slot"], new_hp)
            battle_log.append(
                f"🌿 {wild['name']} ← {move_info.get('emoji','')} **{move_name}**! "
                f"**{damage}** נזק!"
            )

    async def _handle_faint(self, ctx, discord_id, wild, fainted_pokemon, battle_log):
        """כשפוקימון נופל — הצעת החלפה"""
        team = await db.get_team(discord_id)
        alive = [t for t in team if t["current_hp"] > 0]

        await ctx.send(embed=discord.Embed(
            title=f"💀 {fainted_pokemon['name']} חוסר הכרה!",
            color=0xFF4444
        ))

        if not alive:
            await ctx.send(embed=discord.Embed(
                title="😢 כל הפוקימונים שלך נפלו!",
                description="כתוב `!heal` כדי לרפא.",
                color=0xFF4444
            ))
            return None

        return await self._show_switch_menu_forced(ctx, discord_id, alive, battle_log)

    async def _show_switch_menu(self, ctx, discord_id, current_entry, battle_log):
        """תפריט החלפת פוקימון מרצון"""
        team = await db.get_team(discord_id)
        alive = [t for t in team if t["current_hp"] > 0 and t["slot"] != current_entry["slot"]]

        if not alive:
            battle_log.append("❌ אין פוקימונים אחרים להחלפה!")
            return None

        return await self._show_switch_menu_forced(ctx, discord_id, alive, battle_log)

    async def _show_switch_menu_forced(self, ctx, discord_id, alive, battle_log):
        """תפריט בחירת פוקימון — כפתורים"""
        embed = discord.Embed(
            title="🔄 בחר פוקימון!",
            description="בחר פוקימון חי מהשישייה:",
            color=0xFFA500
        )
        entries_to_show = alive[:6]
        for entry in entries_to_show:
            poke = get_pokemon_by_id(entry["pokemon_id"])
            if poke:
                hp_pct = int((entry["current_hp"] / entry["max_hp"]) * 100)
                embed.add_field(
                    name=f"{poke['name']} Lv.{entry['level']}",
                    value=f"❤️ {entry['current_hp']}/{entry['max_hp']} ({hp_pct}%)",
                    inline=True
                )

        view = SwitchView(ctx.author.id, entries_to_show)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        try:
            await msg.edit(view=None)
        except Exception:
            pass

        if view.chosen_index is None:
            return None

        new_entry = entries_to_show[view.chosen_index]
        new_pokemon = get_pokemon_by_id(new_entry["pokemon_id"])
        return new_pokemon, new_entry

    async def _show_inventory_menu(
        self, ctx, discord_id: str, usable: list,
        wild: dict, player_pokemon: dict, player_entry: dict, battle_log: list
    ) -> str:
        """תפריט מלאי — כפתורים"""
        embed = discord.Embed(title="🎒 בחר פריט", color=0x8B4513)
        items_to_show = usable[:9]
        for item in items_to_show:
            info = STORE_ITEMS.get(item["item_name"], {})
            embed.add_field(
                name=f"{info.get('emoji','📦')} {item['item_name']}",
                value=f"כמות: ×{item['quantity']}",
                inline=True
            )

        view = InventoryView(ctx.author.id, items_to_show)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        try:
            await msg.edit(view=None)
        except Exception:
            pass

        if view.chosen_index is None:
            return "cancelled"

        selected = items_to_show[view.chosen_index]
        item_name = selected["item_name"]
        item_info = STORE_ITEMS.get(item_name, {})

        # כדור פוקה
        if item_info.get("type") == "ball":
            removed = await db.remove_item(discord_id, item_name, 1)
            if not removed:
                return "cancelled"

            catch_rate = calculate_catch_rate(wild, item_info.get("catch_rate", 1.0))
            caught = random.random() < catch_rate

            catch_embed = build_catch_embed(wild, caught)
            await ctx.send(embed=catch_embed)

            if caught:
                added = await db.add_to_team(discord_id, wild["id"], wild["max_hp"], wild.get("level", 5))
                if not added:
                    await db.add_to_storage(discord_id, wild["id"], wild["max_hp"], wild.get("level", 5))
                    await ctx.send(f"📦 הצוות מלא! **{wild['name']}** נשלח לאחסון.")
                await db.increment_caught(discord_id)
                await db.add_to_pokedex(discord_id, wild["id"])

                # ── Log catch ──
                rarity_c = get_rarity(wild["id"])
                rarity_map = {"common": "⚪", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟡"}
                r_emoji = rarity_map.get(rarity_c, "⚪")
                await send_log(
                    ctx.bot,
                    category="catch",
                    title="פוקימון נתפס!",
                    description=f"{r_emoji} **{wild['name']}** Lv.{wild.get('level',5)} נתפס בעזרת **{item_name}**",
                    user=ctx.author,
                )

                return "caught"
            else:
                battle_log.append(f"😤 {wild['name']} שחרר את עצמו!")
                await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                return "failed_catch"

        # תרופה
        elif item_info.get("type") == "potion":
            heal = item_info.get("heal", 20)
            removed = await db.remove_item(discord_id, item_name, 1)
            if not removed:
                return "cancelled"
            await db.heal_team_with_potion(discord_id, player_entry["slot"], heal)
            battle_log.append(f"💊 **{item_name}** → {player_pokemon['name']} +**{heal} HP**!")
            return "used_potion"

        return "cancelled"


async def setup(bot):
    await bot.add_cog(BattleCog(bot))
