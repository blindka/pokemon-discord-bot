"""
cogs/battle.py — מערכת קרבות מלאה עם ריאקציות-אימוגים
"""
import discord
from discord.ext import commands
import asyncio
import random

from database import db
from utils.pokemon_utils import (
    get_pokemon_by_id, get_random_wild_pokemon,
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
        self.active_battles: set[str] = set()  # נעילת קרבות כפולים

    @commands.command(name="battle", aliases=["קרב", "fight", "b"])
    async def battle(self, ctx: commands.Context):
        """
        !battle — מתחיל קרב עם פוקימון פראי אקראי
        """
        discord_id = str(ctx.author.id)

        # בדיקה שהמשתמש רשום
        user = await db.get_user(discord_id)
        if not user or not user["starter_selected"]:
            await ctx.send(
                embed=discord.Embed(
                    title="❌ טרם התחלת!",
                    description="כתוב `!start` כדי לבחור פוקימון התחלתי.",
                    color=0xFF4444
                )
            )
            return

        # נעילת קרבות כפולים
        if discord_id in self.active_battles:
            await ctx.send("⚔️ אתה כבר בתוך קרב! סיים אותו קודם.")
            return

        # קבל את השישייה
        team = await db.get_team(discord_id)
        alive_team = [t for t in team if t["current_hp"] > 0]

        if not alive_team:
            await ctx.send(
                embed=discord.Embed(
                    title="💀 כל הפוקימונים שלך מחוסרי הכרה!",
                    description="כתוב `!heal` כדי לרפא אותם במרכז הרפואה.",
                    color=0xFF4444
                )
            )
            return

        # שימוש בפוקימון הראשון החי
        player_entry = alive_team[0]
        player_pokemon = get_pokemon_by_id(player_entry["pokemon_id"])
        if not player_pokemon:
            await ctx.send("❌ שגיאה בטעינת פוקימונים.")
            return

        # יצירת פוקימון פראי
        wild = get_random_wild_pokemon(151)

        # התחל קרב
        self.active_battles.add(discord_id)
        await db.increment_battles(discord_id)

        battle_log = [
            f"🌿 פוקימון פראי הופיע! **{wild['name']}** Lv.{wild.get('level', 5)} רץ לקרב!"
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
        """לולאת הקרב הראשית"""

        while True:
            moves = player_pokemon.get("moves", [])
            num_moves = min(len(moves), 4)

            # בניית Embed + רשימת ריאקציות
            embed, emojis = build_battle_moves_embed(
                player_pokemon, wild, player_entry, battle_log, turn
            )
            msg = await ctx.send(embed=embed)

            for emoji in emojis:
                await msg.add_reaction(emoji)

            # המתנה לריאקציה
            def check(reaction, user_reacted):
                return (
                    user_reacted.id == ctx.author.id
                    and str(reaction.emoji) in emojis
                    and reaction.message.id == msg.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    "reaction_add", timeout=BATTLE_TIMEOUT, check=check
                )
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                await ctx.send(
                    embed=discord.Embed(
                        title="⏰ פג הזמן!",
                        description=f"הקרב נגד {wild['name']} הסתיים בגלל חוסר פעילות.",
                        color=0xFF4444
                    )
                )
                return

            await msg.clear_reactions()
            chosen_emoji = str(reaction.emoji)
            action_index = emojis.index(chosen_emoji)

            # --- בחירת MOVE (0 עד num_moves-1) ---
            if action_index < num_moves:
                move_name = moves[action_index]
                move_info = get_move_info(move_name)
                move_emoji = move_info.get("emoji", "💥")
                is_status = move_info.get("status", False)

                if is_status or move_info.get("power", 0) == 0:
                    # מהלך סטטוס — אין נזק
                    battle_log.append(f"{player_pokemon['name']} השתמש ב-{move_emoji} **{move_name}**!")
                else:
                    damage = calculate_damage(player_pokemon, wild, move_name)
                    crit = is_critical_hit(player_pokemon.get("speed", 50))
                    if crit:
                        damage = int(damage * 1.5)
                    wild["current_hp"] = max(0, wild["current_hp"] - damage)
                    crit_text = " **(קריטי!)**" if crit else ""
                    battle_log.append(
                        f"{player_pokemon['name']} השתמש ב-{move_emoji} **{move_name}**! "
                        f"גרם **{damage}** נזק{crit_text}!"
                    )

                # בדיקת ניצחון
                if wild["current_hp"] <= 0:
                    silver_reward = random.randint(BATTLE_SILVER_REWARD_MIN, BATTLE_SILVER_REWARD_MAX)
                    await db.update_silver(discord_id, silver_reward)
                    victory_embed = discord.Embed(
                        title=f"🏆 ניצחת! {wild['name']} חוסר הכרה!",
                        description=(
                            f"✅ **{wild['name']}** הובס!\n"
                            f"💰 קיבלת **{silver_reward} Silver** כפרס!"
                        ),
                        color=0x00FF00
                    )
                    victory_embed.set_thumbnail(url=get_sprite_url(wild["id"]))
                    await ctx.send(embed=victory_embed)
                    return

                # תור הפוקימון הפראי
                await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)

                # בדיקת הפסד
                if player_entry["current_hp"] <= 0:
                    lose_embed = discord.Embed(
                        title=f"💀 {player_pokemon['name']} חוסר הכרה!",
                        description=(
                            f"😢 **{player_pokemon['name']}** הובס על ידי {wild['name']}!\n"
                            "כתוב `!heal` כדי לרפא את הצוות."
                        ),
                        color=0xFF4444
                    )
                    await ctx.send(embed=lose_embed)
                    await db.update_team_pokemon_hp(discord_id, player_entry["slot"], 0)
                    return

            # --- מלאי (action_index == num_moves) ---
            elif action_index == num_moves:
                inv = await db.get_inventory(discord_id)
                usable = [i for i in inv if i["item_name"] in
                          ["Poké Ball", "Great Ball", "Ultra Ball",
                           "Potion", "Super Potion", "Hyper Potion"]]

                if not usable:
                    battle_log.append("🎒 המלאי ריק!")
                    await ctx.send("🎒 המלאי שלך ריק! אין מה להשתמש.", delete_after=5)
                else:
                    # בחירת פריט מהמלאי
                    item_result = await self._show_inventory_menu(ctx, discord_id, usable, wild, player_pokemon, player_entry, battle_log)
                    if item_result == "caught":
                        return
                    elif item_result == "used_potion":
                        # refresh player_entry
                        team = await db.get_team(discord_id)
                        for t in team:
                            if t["slot"] == player_entry["slot"]:
                                player_entry = t
                                break

            # --- ברח (action_index == num_moves+1) ---
            else:
                escape_chance = 0.5
                if random.random() < escape_chance:
                    await ctx.send(
                        embed=discord.Embed(
                            title="🏃 ברחת!",
                            description=f"ברחת מהקרב נגד **{wild['name']}**.",
                            color=0xFFA500
                        )
                    )
                    return
                else:
                    battle_log.append(f"🏃 לא הצלחת לברוח!")
                    # Wild attacks anyway
                    await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                    if player_entry["current_hp"] <= 0:
                        await db.update_team_pokemon_hp(discord_id, player_entry["slot"], 0)
                        return

            turn += 1

    async def _wild_attack(self, ctx, discord_id, player_pokemon, player_entry, wild, battle_log):
        """תקיפה של הפוקימון הפראי"""
        wild_moves = wild.get("moves", ["Tackle"])
        move_name = random.choice(wild_moves)
        move_info = get_move_info(move_name)

        if move_info.get("status", False) or move_info.get("power", 0) == 0:
            battle_log.append(f"🌿 {wild['name']} השתמש ב-{move_info.get('emoji','')} **{move_name}**!")
        else:
            damage = calculate_wild_damage(wild, player_pokemon)
            new_hp = max(0, player_entry["current_hp"] - damage)
            player_entry["current_hp"] = new_hp
            await db.update_team_pokemon_hp(discord_id, player_entry["slot"], new_hp)
            battle_log.append(
                f"🌿 {wild['name']} השתמש ב-{move_info.get('emoji','')} **{move_name}**! "
                f"גרם **{damage}** נזק!"
            )

    async def _show_inventory_menu(
        self, ctx, discord_id: str, usable: list,
        wild: dict, player_pokemon: dict, player_entry: dict, battle_log: list
    ) -> str:
        """מציג תפריט מלאי בתוך הקרב"""
        from config import STORE_ITEMS

        embed = discord.Embed(
            title="🎒 בחר פריט לשימוש",
            color=0x8B4513
        )
        emojis = []
        items_to_show = usable[:9]

        item_text = ""
        for i, item in enumerate(items_to_show):
            info = STORE_ITEMS.get(item["item_name"], {})
            emoji = NUMBER_EMOJIS[i]
            item_text += f"{emoji} **{item['item_name']}** × {item['quantity']}\n"
            emojis.append(emoji)

        # כפתור ביטול
        cancel_emoji = "❌"
        item_text += f"{cancel_emoji} **ביטול**"
        emojis.append(cancel_emoji)

        embed.add_field(name="פריטים זמינים:", value=item_text)
        msg = await ctx.send(embed=embed)
        for e in emojis:
            await msg.add_reaction(e)

        def check(r, u):
            return (
                u.id == ctx.author.id
                and str(r.emoji) in emojis
                and r.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
            return "cancelled"

        await msg.delete()
        chosen = str(reaction.emoji)

        if chosen == cancel_emoji:
            return "cancelled"

        idx = emojis.index(chosen)
        if idx >= len(items_to_show):
            return "cancelled"

        selected = items_to_show[idx]
        item_name = selected["item_name"]
        item_info = STORE_ITEMS.get(item_name, {})

        # --- שימוש בכדור פוקה ---
        if item_info.get("type") == "ball":
            removed = await db.remove_item(discord_id, item_name, 1)
            if not removed:
                await ctx.send("❌ אין לך את הפריט הזה!", delete_after=5)
                return "cancelled"

            catch_rate = calculate_catch_rate(wild, item_info.get("catch_rate", 1.0))
            caught = random.random() < catch_rate

            catch_embed = build_catch_embed(wild, caught)
            await ctx.send(embed=catch_embed)

            if caught:
                # הוסף לצוות/אחסון
                team = await db.get_team(discord_id)
                added = await db.add_to_team(discord_id, wild["id"], wild["max_hp"], wild.get("level", 5))
                if not added:
                    await db.add_to_storage(discord_id, wild["id"], wild["max_hp"], wild.get("level", 5))
                    await ctx.send(f"📦 הצוות מלא! **{wild['name']}** נשלח לאחסון.")

                await db.increment_caught(discord_id)
                await db.add_to_pokedex(discord_id, wild["id"])
                return "caught"
            else:
                battle_log.append(f"😤 {wild['name']} שחרר את עצמו מה-{item_name}!")
                # Wild attacks after failed catch
                await self._wild_attack(ctx, discord_id, player_pokemon, player_entry, wild, battle_log)
                return "failed_catch"

        # --- שימוש בתרופה ---
        elif item_info.get("type") == "potion":
            heal = item_info.get("heal", 20)
            removed = await db.remove_item(discord_id, item_name, 1)
            if not removed:
                await ctx.send("❌ אין לך את הפריט הזה!", delete_after=5)
                return "cancelled"

            await db.heal_team_with_potion(discord_id, player_entry["slot"], heal)
            battle_log.append(f"💊 השתמשת ב-**{item_name}**! {player_pokemon['name']} רפא **{heal} HP**!")
            await ctx.send(f"💊 **{player_pokemon['name']}** רפא **{heal} HP**!", delete_after=5)
            return "used_potion"

        return "cancelled"


async def setup(bot):
    await bot.add_cog(BattleCog(bot))
