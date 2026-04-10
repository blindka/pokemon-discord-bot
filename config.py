"""
config.py — הגדרות גלובליות של הבוט
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ===== BOT SETTINGS =====
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_TOKEN_HERE")
PREFIX = "!"
BOT_VERSION = "1.0.0"

# ===== GAME ECONOMY =====
STARTING_SILVER = 1000
BATTLE_SILVER_REWARD_MIN = 10
BATTLE_SILVER_REWARD_MAX = 100

# ===== STORE PRICES =====
STORE_ITEMS = {
    "Poké Ball":    {"price": 200, "catch_rate": 1.0,  "type": "ball",   "emoji": "🔴"},
    "Great Ball":   {"price": 600, "catch_rate": 1.5,  "type": "ball",   "emoji": "🔵"},
    "Ultra Ball":   {"price": 1200,"catch_rate": 2.0,  "type": "ball",   "emoji": "⚫"},
    "Potion":       {"price": 300, "heal": 20,          "type": "potion", "emoji": "🧪"},
    "Super Potion": {"price": 700, "heal": 60,          "type": "potion", "emoji": "💊"},
    "Hyper Potion": {"price": 1500,"heal": 120,         "type": "potion", "emoji": "💉"},
}

STARTING_ITEMS = {"Poké Ball": 5}

# ===== BATTLE SETTINGS =====
BATTLE_TIMEOUT = 60       # שניות לתור
WILD_POKEMON_POOL = 151   # Gen 1 only

# ===== TYPE COLORS (for Discord Embeds) =====
TYPE_COLORS = {
    "Normal":   0xA8A878,
    "Fire":     0xF08030,
    "Water":    0x6890F0,
    "Electric": 0xF8D030,
    "Grass":    0x78C850,
    "Ice":      0x98D8D8,
    "Fighting": 0xC03028,
    "Poison":   0xA040A0,
    "Ground":   0xE0C068,
    "Flying":   0xA890F0,
    "Psychic":  0xF85888,
    "Bug":      0xA8B820,
    "Rock":     0xB8A038,
    "Ghost":    0x705898,
    "Dragon":   0x7038F8,
    "Dark":     0x705848,
    "Steel":    0xB8B8D0,
    "Fairy":    0xEE99AC,
}

TYPE_EMOJIS = {
    "Normal":   "⬜",
    "Fire":     "🔥",
    "Water":    "💧",
    "Electric": "⚡",
    "Grass":    "🌿",
    "Ice":      "❄️",
    "Fighting": "🥊",
    "Poison":   "☠️",
    "Ground":   "🌍",
    "Flying":   "🌪️",
    "Psychic":  "🔮",
    "Bug":      "🐛",
    "Rock":     "🪨",
    "Ghost":    "👻",
    "Dragon":   "🐉",
    "Dark":     "🌑",
    "Steel":    "⚙️",
    "Fairy":    "🧚",
}

# ===== STARTER POKEMON IDs =====
STARTER_IDS = [1, 4, 7]  # Bulbasaur, Charmander, Squirtle

# ===== NUMBER EMOJIS =====
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# ===== DATABASE =====
DB_PATH = "data/pokemon_bot.db"
