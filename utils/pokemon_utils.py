"""
utils/pokemon_utils.py — פונקציות עזר לנתוני פוקימונים
"""
import json
import random
from typing import Optional, List
import os

# טעינת נתוני פוקימון מהקובץ
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pokemon_data.json")
with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _ALL_POKEMON = json.load(f)["pokemon"]

# מיפוי ID -> נתונים
_POKEMON_BY_ID = {p["id"]: p for p in _ALL_POKEMON}
_POKEMON_BY_NAME = {p["name"].lower(): p for p in _ALL_POKEMON}


def get_pokemon_by_id(pokemon_id: int) -> Optional[dict]:
    return _POKEMON_BY_ID.get(pokemon_id)


def get_pokemon_by_name(name: str) -> Optional[dict]:
    return _POKEMON_BY_NAME.get(name.lower())


def get_all_pokemon() -> List[dict]:
    return _ALL_POKEMON


def get_random_wild_pokemon(max_id: int = 151) -> Optional[dict]:
    """מחזיר פוקימון פראי אקראי עם HP מלא"""
    chosen = random.choice([p for p in _ALL_POKEMON if p["id"] <= max_id])
    return {
        **chosen,
        "current_hp": chosen["hp"],
        "max_hp": chosen["hp"],
        "level": random.randint(3, 15),
    }


def get_sprite_url(pokemon_id: int) -> str:
    """מחזיר URL של sprite מה-PokeAPI"""
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"


def get_animated_sprite_url(pokemon_id: int) -> str:
    """מחזיר animated gif sprite"""
    return (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/versions/generation-v/black-white/animated/{pokemon_id}.gif"
    )


def build_hp_bar(current: int, maximum: int, length: int = 10) -> str:
    """מייצר פס HP גרפי"""
    if maximum == 0:
        return "░" * length
    filled = round((current / maximum) * length)
    filled = max(0, min(filled, length))
    bar = "█" * filled + "░" * (length - filled)
    pct = (current / maximum) * 100
    if pct > 50:
        color = "🟢"
    elif pct > 20:
        color = "🟡"
    else:
        color = "🔴"
    return f"{color} `{bar}` {current}/{maximum}"


def get_type_emoji(pokemon_type: str) -> str:
    from config import TYPE_EMOJIS
    return TYPE_EMOJIS.get(pokemon_type, "❓")


def get_primary_color(pokemon: dict) -> int:
    from config import TYPE_COLORS
    types = pokemon.get("type", ["Normal"])
    return TYPE_COLORS.get(types[0], 0xA8A878)


def format_pokemon_types(types: list) -> str:
    from config import TYPE_EMOJIS
    return " / ".join(f"{TYPE_EMOJIS.get(t, '')} {t}" for t in types)


def calculate_catch_rate(wild_pokemon: dict, ball_multiplier: float = 1.0) -> float:
    """
    חישוב סיכוי תפיסה — בהתחשב ב-HP נותר וסוג הכדור
    """
    hp_ratio = wild_pokemon["current_hp"] / wild_pokemon["max_hp"]
    base_rate = 0.35  # 35% base
    hp_bonus = (1 - hp_ratio) * 0.35  # עד 35% בונוס כש-HP נמוך
    catch_chance = (base_rate + hp_bonus) * ball_multiplier
    return min(catch_chance, 0.95)  # cap at 95%


def get_starters() -> List[Optional[dict]]:
    """מחזיר את 3 הפוקימונים ההתחלתיים"""
    from config import STARTER_IDS
    return [get_pokemon_by_id(pid) for pid in STARTER_IDS]
