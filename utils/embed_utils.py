"""
utils/embed_utils.py — יצירת Discord Embeds יפים
"""
import discord
from typing import Optional, List, Tuple
from utils.pokemon_utils import (
    get_sprite_url, get_animated_sprite_url,
    build_hp_bar, get_primary_color, format_pokemon_types, get_type_emoji
)
from config import TYPE_COLORS, TYPE_EMOJIS


def build_pokemon_embed(pokemon_data: dict, title: str = None, team_entry: dict = None) -> discord.Embed:
    """
    Embed כללי למידע על פוקימון.
    team_entry: שורה מבסיס הנתונים עם HP נוכחי.
    """
    types = pokemon_data.get("type", ["Normal"])
    color = get_primary_color(pokemon_data)
    name = pokemon_data["name"]
    pid = pokemon_data["id"]

    embed = discord.Embed(
        title=title or f"#{pid} — {name}",
        color=color,
    )
    embed.set_thumbnail(url=get_sprite_url(pid))

    # Types
    embed.add_field(name="סוג", value=format_pokemon_types(types), inline=True)

    # Level & HP (if team entry provided)
    if team_entry:
        level = team_entry.get("level", pokemon_data.get("level", 5))
        cur_hp = team_entry.get("current_hp", pokemon_data["hp"])
        max_hp = team_entry.get("max_hp", pokemon_data["hp"])
        embed.add_field(name="רמה", value=f"⭐ {level}", inline=True)
        embed.add_field(name="HP", value=build_hp_bar(cur_hp, max_hp), inline=False)
    else:
        embed.add_field(name="HP נבסיס", value=f"❤️ {pokemon_data['hp']}", inline=True)
        embed.add_field(name="רמה", value=f"⭐ {pokemon_data.get('level', 5)}", inline=True)

    # Stats
    stats = (
        f"⚔️ Attack: **{pokemon_data['attack']}**\n"
        f"🛡️ Defense: **{pokemon_data['defense']}**\n"
        f"💨 Speed: **{pokemon_data['speed']}**"
    )
    embed.add_field(name="סטטיסטיקות", value=stats, inline=False)

    # Moves
    moves = pokemon_data.get("moves", [])
    if moves:
        move_str = " • ".join(f"`{m}`" for m in moves)
        embed.add_field(name="מהלכים", value=move_str, inline=False)

    embed.set_footer(text=f"Pokémon #{pid}")
    return embed


def build_battle_embed(
    player_pokemon: dict, player_team_entry: dict,
    wild_pokemon: dict,
    battle_log: list[str],
    turn: int = 1
) -> discord.Embed:
    """Embed לקרב פעיל"""
    from utils.battle_utils import format_battle_log

    types = player_pokemon.get("type", ["Normal"])
    color = get_primary_color(player_pokemon)

    embed = discord.Embed(
        title="⚔️ קרב פוקימונים!",
        color=color,
    )

    # Wild pokemon info
    wild_hp_bar = build_hp_bar(wild_pokemon["current_hp"], wild_pokemon["max_hp"])
    wild_type_str = format_pokemon_types(wild_pokemon.get("type", ["Normal"]))
    embed.add_field(
        name=f"🌿 {wild_pokemon['name']} (פראי) — רמה {wild_pokemon.get('level', 5)}",
        value=f"{wild_type_str}\n{wild_hp_bar}",
        inline=False
    )

    embed.set_thumbnail(url=get_sprite_url(wild_pokemon["id"]))

    # Divider
    embed.add_field(name="⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯", value="\u200b", inline=False)

    # Player pokemon info
    cur_hp = player_team_entry.get("current_hp", player_pokemon["hp"])
    max_hp = player_team_entry.get("max_hp", player_pokemon["hp"])
    player_hp_bar = build_hp_bar(cur_hp, max_hp)
    player_type_str = format_pokemon_types(types)
    level = player_team_entry.get("level", player_pokemon.get("level", 5))

    embed.add_field(
        name=f"🏆 {player_pokemon['name']} שלך — רמה {level}",
        value=f"{player_type_str}\n{player_hp_bar}",
        inline=False
    )

    embed.set_image(url=get_sprite_url(player_pokemon["id"]))

    # Battle log
    if battle_log:
        from utils.battle_utils import format_battle_log
        embed.add_field(
            name="📜 יומן קרב",
            value=format_battle_log(battle_log),
            inline=False
        )

    embed.set_footer(text=f"תור {turn} | בחר מהלך בעזרת ריאקציות 👇")
    return embed


def build_battle_moves_embed(player_pokemon: dict, wild_pokemon: dict,
                              player_team_entry: dict, battle_log: list,
                              turn: int) -> tuple[discord.Embed, list[str]]:
    """מחזיר embed + רשימת האימוגים לריאקציות"""
    from config import NUMBER_EMOJIS
    from utils.battle_utils import get_move_info

    embed = build_battle_embed(player_pokemon, player_team_entry, wild_pokemon, battle_log, turn)

    moves = player_pokemon.get("moves", [])
    move_text = ""
    emojis = []

    for i, move_name in enumerate(moves[:4]):
        info = get_move_info(move_name)
        emoji = NUMBER_EMOJIS[i]
        power_str = f"(עוצמה: {info['power']})" if info["power"] > 0 else "(סטטוס)"
        move_text += f"{emoji} **{move_name}** {info['emoji']} {power_str}\n"
        emojis.append(emoji)

    # Extra options
    move_text += f"{NUMBER_EMOJIS[len(moves)]} 🎒 **פתח מלאי** (השתמש בפריט)\n"
    emojis.append(NUMBER_EMOJIS[len(moves)])

    move_text += f"{NUMBER_EMOJIS[len(moves)+1]} 🏃 **ברח מהקרב**\n"
    emojis.append(NUMBER_EMOJIS[len(moves)+1])

    embed.add_field(name="🎯 בחר פעולה:", value=move_text, inline=False)
    return embed, emojis


def build_profile_embed(user: dict, team: list, pokemon_data_map: dict) -> discord.Embed:
    """Embed לפרופיל שחקן"""
    embed = discord.Embed(
        title=f"🏆 פרופיל — {user['username']}",
        color=0xFFD700
    )

    import json
    pokedex = json.loads(user.get("pokedex_ids", "[]"))

    embed.add_field(name="💰 כסף", value=f"**{user['silver']}** Silver", inline=True)
    embed.add_field(name="⚔️ קרבות", value=str(user["total_battles"]), inline=True)
    embed.add_field(name="🔴 נתפסו", value=str(user["pokemon_caught"]), inline=True)
    embed.add_field(name="📖 פוקידקס", value=f"{len(pokedex)}/151", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    if team:
        team_str = ""
        for entry in team:
            pdata = pokemon_data_map.get(entry["pokemon_id"])
            if pdata:
                type_emoji = get_type_emoji(pdata["type"][0])
                hp_status = "✅" if entry["current_hp"] > 0 else "💀"
                team_str += (
                    f"{hp_status} {type_emoji} **{pdata['name']}** "
                    f"Lv.{entry['level']} — HP {entry['current_hp']}/{entry['max_hp']}\n"
                )
        embed.add_field(name="🐾 שישייה", value=team_str or "ריק", inline=False)
    else:
        embed.add_field(name="🐾 שישייה", value="אין פוקימונים!", inline=False)

    embed.set_footer(text="!השתמש בפקודות כדי לשחק")
    return embed


def build_store_embed(silver: int) -> discord.Embed:
    """Embed לחנות"""
    from config import STORE_ITEMS

    embed = discord.Embed(
        title="🏪 חנות פוקימון",
        description=f"💰 יתרה: **{silver} Silver**\n\nהשתמש ב-`!buy <שם פריט>` לקנייה",
        color=0x00C851
    )

    balls_str = ""
    potions_str = ""

    for name, info in STORE_ITEMS.items():
        line = f"{info['emoji']} **{name}** — {info['price']} Silver\n"
        if info["type"] == "ball":
            balls_str += line
        else:
            potions_str += line

    embed.add_field(name="🔴 כדורי פוקה", value=balls_str, inline=False)
    embed.add_field(name="💊 תרופות", value=potions_str, inline=False)
    embed.set_footer(text='דוגמה: !buy "Poké Ball"')
    return embed


def build_inventory_embed(inventory: list, username: str) -> discord.Embed:
    """Embed למלאי"""
    from config import STORE_ITEMS

    embed = discord.Embed(
        title=f"🎒 המלאי של {username}",
        color=0x8B4513
    )

    if not inventory:
        embed.description = "המלאי ריק! לך לחנות עם `!store`"
        return embed

    inv_str = ""
    for item in inventory:
        name = item["item_name"]
        qty = item["quantity"]
        info = STORE_ITEMS.get(name, {})
        emoji = info.get("emoji", "📦")
        inv_str += f"{emoji} **{name}** × {qty}\n"

    embed.add_field(name="פריטים", value=inv_str, inline=False)
    embed.set_footer(text="!השתמש בפריט: !use <שם פריט>")
    return embed


def build_catch_embed(wild_pokemon: dict, success: bool) -> discord.Embed:
    """Embed לתפיסת פוקימון"""
    if success:
        color = 0x00FF00
        title = f"🔴 נתפס! {wild_pokemon['name']} הצטרף לצוות שלך!"
        desc = f"✅ **{wild_pokemon['name']}** נתפס בהצלחה!"
    else:
        color = 0xFF4444
        title = f"❌ {wild_pokemon['name']} ברח!"
        desc = f"💨 **{wild_pokemon['name']}** הצליח להימלט!"

    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=get_sprite_url(wild_pokemon["id"]))
    return embed


def build_starter_embed() -> tuple[discord.Embed, list[str]]:
    """Embed לבחירת פוקימון התחלתי"""
    from config import NUMBER_EMOJIS
    from utils.pokemon_utils import get_starters

    starters = get_starters()
    embed = discord.Embed(
        title="🌟 ברוך הבא לעולם הפוקימונים!",
        description="**בחר את הפוקימון ההתחלתי שלך** על ידי לחיצה על האימוג'י המתאים:",
        color=0xFFD700
    )

    emojis = []
    for i, poke in enumerate(starters):
        if poke:
            type_emoji = get_type_emoji(poke["type"][0])
            type_name = poke["type"][0]
            emoji = NUMBER_EMOJIS[i]
            embed.add_field(
                name=f"{emoji} {poke['name']}",
                value=(
                    f"{type_emoji} **סוג:** {type_name}\n"
                    f"❤️ **HP:** {poke['hp']}\n"
                    f"⚔️ **Attack:** {poke['attack']}\n"
                    f"🛡️ **Defense:** {poke['defense']}"
                ),
                inline=True
            )
            emojis.append(emoji)

    embed.set_footer(text="לחץ על 1️⃣ Bulbasaur  |  2️⃣ Charmander  |  3️⃣ Squirtle")
    return embed, emojis
