"""
cogs/battle.py — מערכת קרבות מלאה עם חלון מתמשך (edit-in-place)
"""
import discord
from discord.ext import commands
import asyncio
import random

from database import db
from utils.pokemon_utils import (
    get_pokemon_by_id, get_wild_pokemon_for_zone,
    build_hp_bar, get_sprite_url, calculate_catch_rate
)
from utils.battle_utils import (
    calculate_damage, calculate_wild_damage,
    is_critical_hit, get_move_info, format_battle_log
)
from utils.embed_utils import build_battle_moves_embed, build_catch_embed
from config import (
    BATTLE_TIMEOUT, NUMBER_EMOJIS,
    BATTLE_SILVER_REWARD_MIN, BATTLE_SILVER_REWARD_MAX,
    STORE_ITEMS
)


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

        # פוקימון פראי בהתאם לאזור ורמת השחקן
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
        """לולאת הקרב — חלון מתמשך (edit-in-place)"""
        battle_msg = None  # ההודעה הקבועה שנערוך בכל תור

        while True:
            moves = player_pokemon.get("moves", [])
            num_moves = min(len(moves), 4)

            # בניית Embed + ריאקציות
            embed, emojis = build_battle_moves_embed(
                player_pokemon, wild, player_entry, battle_log, turn
            )

            if battle_msg is None:
                # תור ראשון — שלח הודעה חדשה
                battle_msg = await ctx.send(embed=embed)
            else:
                # תורים הבאים — ערוך את אותה הודעה
                await battle_msg.edit(embed=embed)
                try:
                    await battle_msg.clear_reactions()
                except Exception:
                    pass

            # ריאקציות במקביל
            await asyncio.gather(*[battle_msg.add_reaction(e) for e in emojis])

            def check(reaction, user_reacted):
                return (
                    user_reacted.id == ctx.author.id
                    and str(reaction.emoji) in emojis
                    and reaction.message.id == battle_msg.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=BATTLE_TIMEOUT, check=check
                )
            except asyncio.TimeoutError:
                try:
                    await battle_msg.clear_reactions()
                except Exception:
                    pass
                await ctx.send(embed=discord.Embed(
                    title="⏰ פג הזמן!",
                    description=f"הקרב נגד {wild['name']} הסתיים.",
                    color=0xFF4444
                ))
                return

            # הסר רק את הריאקציה של המשתמש (מהיר יותר מ-clear_reactions)
            try:
                await battle_msg.remove_reaction(reaction.emoji, ctx.author)
            except Exception:
                pass

            chosen_emoji = str(reaction.emoji)
            action_index = emojis.index(chosen_emoji)

            # --- MOVE (0 עד num_moves-1) ---
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

                # ניצחון?
                if wild["current_hp"] <= 0:
                    await self._handle_victory(
                        ctx, discord_id, player_entry, wild, battle_msg
                    )
                    return

                # תור הפראי
                await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)

                # הפסד?
                if player_entry["current_hp"] <= 0:
                    switched = await self._handle_faint(ctx, discord_id, wild, player_pokemon, battle_log)
                    if switched is None:
                        return
                    player_pokemon, player_entry = switched

            # --- מלאי (action_index == num_moves) ---
            elif action_index == num_moves:
                inv = await db.get_inventory(discord_id)
                usable = [i for i in inv if i["item_name"] in
                          ["Poké Ball", "Great Ball", "Ultra Ball",
                           "Potion", "Super Potion", "Hyper Potion"]]

                if not usable:
                    battle_log.append("🎒 המלאי ריק!")
                else:
                    item_result = await self._show_inventory_menu(
                        ctx, discord_id, usable, wild, player_pokemon, player_entry, battle_log
                    )
                    if item_result == "caught":
                        try:
                            await battle_msg.clear_reactions()
                        except Exception:
                            pass
                        return
                    elif item_result == "used_potion":
                        team = await db.get_team(discord_id)
                        for t in team:
                            if t["slot"] == player_entry["slot"]:
                                player_entry = t
                                break

            # --- החלפת פוקימון (action_index == num_moves+1) ---
            elif action_index == num_moves + 1:
                switched = await self._show_switch_menu(ctx, discord_id, player_entry, battle_log)
                if switched:
                    player_pokemon, player_entry = switched
                    battle_log.append(f"🔄 קדימה, **{player_pokemon['name']}**!")
                    # עולה בתור — הפראי תוקף
                    await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                    if player_entry["current_hp"] <= 0:
                        sw = await self._handle_faint(ctx, discord_id, wild, player_pokemon, battle_log)
                        if sw is None:
                            return
                        player_pokemon, player_entry = sw
                else:
                    battle_log.append("❌ ביטלת את ההחלפה.")

            # --- ברח (action_index == num_moves+2) ---
            elif action_index == num_moves + 2:
                if random.random() < 0.5:
                    try:
                        await battle_msg.clear_reactions()
                    except Exception:
                        pass
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
        """טיפול בניצחון — XP, כסף, Level Up, אבולוציה"""
        silver_reward = random.randint(BATTLE_SILVER_REWARD_MIN, BATTLE_SILVER_REWARD_MAX)
        await db.update_silver(discord_id, silver_reward)

        # XP via Gen-1 formula: (base_exp * wild_level) / 7
        # baseExp is sourced from PokéAPI (official data)
        base_exp = wild.get("baseExp", 100)
        wild_level = wild.get("level", 5)
        xp_gained = max(int(base_exp * wild_level / 7), 10)

        xp_result = await db.give_exp_and_check_levelup(
            discord_id, player_entry["slot"], xp_gained
        )

        desc = (
            f"✅ **{wild['name']}** הובס!\n"
            f"💰 **{silver_reward} Silver**\n"
            f"⭐ **{xp_gained} XP**"
        )

        if xp_result["leveled_up"]:
            desc += f"\n\n🎉 **Level Up! רמה {xp_result['new_level']}!**"

        if xp_result["evolved_to"]:
            new_poke = get_pokemon_by_id(xp_result["evolved_to"])
            old_poke = get_pokemon_by_id(xp_result["old_pokemon_id"])
            old_name = old_poke["name"] if old_poke else "?"
            new_name = new_poke["name"] if new_poke else "?"
            desc += f"\n\n✨🌟 **{old_name} מתפתח ל-{new_name}!!** 🌟✨"

        victory_embed = discord.Embed(
            title=f"🏆 ניצחת!",
            description=desc,
            color=0x00FF00
        )
        victory_embed.set_thumbnail(url=get_sprite_url(wild["id"]))
        if xp_result.get("evolved_to"):
            new_poke = get_pokemon_by_id(xp_result["evolved_to"])
            if new_poke:
                victory_embed.set_image(url=get_sprite_url(new_poke["id"]))

        try:
            await battle_msg.clear_reactions()
        except Exception:
            pass
        await ctx.send(embed=victory_embed)

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
        await db.update_team_pokemon_hp(discord_id, -1, 0)  # placeholder
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
        """תפריט החלפת פוקימון מרצון (עולה תור)"""
        team = await db.get_team(discord_id)
        alive = [t for t in team if t["current_hp"] > 0 and t["slot"] != current_entry["slot"]]

        if not alive:
            battle_log.append("❌ אין פוקימונים אחרים להחלפה!")
            return None

        return await self._show_switch_menu_forced(ctx, discord_id, alive, battle_log)

    async def _show_switch_menu_forced(self, ctx, discord_id, alive, battle_log):
        """תפריט בחירת פוקימון (משותף לכפויה ומרצון)"""
        embed = discord.Embed(
            title="🔄 בחר פוקימון!",
            description="בחר פוקימון חי מהשישייה:",
            color=0xFFA500
        )

        emojis = []
        entries_to_show = alive[:6]
        for i, entry in enumerate(entries_to_show):
            poke = get_pokemon_by_id(entry["pokemon_id"])
            if poke:
                emoji = NUMBER_EMOJIS[i]
                hp_pct = int((entry["current_hp"] / entry["max_hp"]) * 100)
                embed.add_field(
                    name=f"{emoji} {poke['name']} Lv.{entry['level']}",
                    value=f"❤️ {entry['current_hp']}/{entry['max_hp']} ({hp_pct}%)",
                    inline=True
                )
                emojis.append(emoji)

        # ביטול (רק אם מרצון — כלומר אם יש יותר מ-0 חיים)
        cancel_emoji = "❌"
        emojis.append(cancel_emoji)
        embed.set_footer(text="❌ = ביטול")

        msg = await ctx.send(embed=embed)
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
            try:
                await msg.delete()
            except Exception:
                pass
            return None

        try:
            await msg.delete()
        except Exception:
            pass

        chosen = str(reaction.emoji)
        if chosen == cancel_emoji:
            return None

        idx = emojis.index(chosen)
        if idx >= len(entries_to_show):
            return None

        new_entry = entries_to_show[idx]
        new_pokemon = get_pokemon_by_id(new_entry["pokemon_id"])
        return new_pokemon, new_entry

    async def _show_inventory_menu(
        self, ctx, discord_id: str, usable: list,
        wild: dict, player_pokemon: dict, player_entry: dict, battle_log: list
    ) -> str:
        """תפריט מלאי בתוך הקרב"""
        embed = discord.Embed(title="🎒 בחר פריט", color=0x8B4513)
        emojis = []
        items_to_show = usable[:9]

        item_text = ""
        for i, item in enumerate(items_to_show):
            emoji = NUMBER_EMOJIS[i]
            item_text += f"{emoji} **{item['item_name']}** × {item['quantity']}\n"
            emojis.append(emoji)

        cancel_emoji = "❌"
        item_text += f"{cancel_emoji} **ביטול**"
        emojis.append(cancel_emoji)

        embed.add_field(name="פריטים:", value=item_text)
        msg = await ctx.send(embed=embed)
        await asyncio.gather(*[msg.add_reaction(e) for e in emojis])

        def check(r, u):
            return u.id == ctx.author.id and str(r.emoji) in emojis and r.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            try:
                await msg.delete()
            except Exception:
                pass
            return "cancelled"

        try:
            await msg.delete()
        except Exception:
            pass
        chosen = str(reaction.emoji)

        if chosen == cancel_emoji:
            return "cancelled"

        idx = emojis.index(chosen)
        if idx >= len(items_to_show):
            return "cancelled"

        selected = items_to_show[idx]
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
