"""
database/db.py — שכבת בסיס הנתונים עם SQLite ואסינכרוניות
"""
import aiosqlite
import json
from config import DB_PATH, STARTING_SILVER, STARTING_ITEMS


async def init_db():
    """יוצר את כל הטבלאות אם לא קיימות"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                silver INTEGER DEFAULT 1000,
                total_battles INTEGER DEFAULT 0,
                pokemon_caught INTEGER DEFAULT 0,
                pokedex_ids TEXT DEFAULT '[]',
                starter_selected INTEGER DEFAULT 0,
                current_zone TEXT DEFAULT 'grass',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration: add current_zone if column doesn't exist yet
        try:
            await db.execute("ALTER TABLE users ADD COLUMN current_zone TEXT DEFAULT 'grass'")
        except Exception:
            pass  # Column already exists

        await db.execute("""
            CREATE TABLE IF NOT EXISTS team (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                pokemon_id INTEGER NOT NULL,
                current_hp INTEGER NOT NULL,
                max_hp INTEGER NOT NULL,
                level INTEGER DEFAULT 5,
                exp INTEGER DEFAULT 0,
                exp_to_next INTEGER DEFAULT 125,
                slot INTEGER NOT NULL,
                FOREIGN KEY (discord_id) REFERENCES users(discord_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS storage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                pokemon_id INTEGER NOT NULL,
                current_hp INTEGER NOT NULL,
                max_hp INTEGER NOT NULL,
                level INTEGER DEFAULT 5,
                exp INTEGER DEFAULT 0,
                FOREIGN KEY (discord_id) REFERENCES users(discord_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 0,
                UNIQUE(discord_id, item_name),
                FOREIGN KEY (discord_id) REFERENCES users(discord_id)
            )
        """)
        await db.commit()


# ============================================================
# USER
# ============================================================

async def get_user(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(discord_id: str, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (discord_id, username, silver) VALUES (?, ?, ?)",
            (discord_id, username, STARTING_SILVER)
        )
        # Add starting items
        for item_name, qty in STARTING_ITEMS.items():
            await db.execute(
                "INSERT OR IGNORE INTO inventory (discord_id, item_name, quantity) VALUES (?, ?, ?)",
                (discord_id, item_name, qty)
            )
        await db.commit()


async def update_silver(discord_id: str, amount: int):
    """מוסיף/מוריד כסף. מחזיר את הסכום החדש."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET silver = MAX(0, silver + ?) WHERE discord_id = ?",
            (amount, discord_id)
        )
        await db.commit()
        async with db.execute(
            "SELECT silver FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_silver(discord_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT silver FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def increment_battles(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET total_battles = total_battles + 1 WHERE discord_id = ?",
            (discord_id,)
        )
        await db.commit()


async def increment_caught(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET pokemon_caught = pokemon_caught + 1 WHERE discord_id = ?",
            (discord_id,)
        )
        await db.commit()


async def add_to_pokedex(discord_id: str, pokemon_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT pokedex_ids FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return
            ids = json.loads(row[0])
            if pokemon_id not in ids:
                ids.append(pokemon_id)
                await db.execute(
                    "UPDATE users SET pokedex_ids = ? WHERE discord_id = ?",
                    (json.dumps(ids), discord_id)
                )
                await db.commit()


async def set_starter_selected(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET starter_selected = 1 WHERE discord_id = ?",
            (discord_id,)
        )
        await db.commit()


# ============================================================
# TEAM
# ============================================================

async def get_team(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM team WHERE discord_id = ? ORDER BY slot ASC",
            (discord_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def add_to_team(discord_id: str, pokemon_id: int, max_hp: int, level: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        # Find next available slot (max 6)
        async with db.execute(
            "SELECT COUNT(*) FROM team WHERE discord_id = ?", (discord_id,)
        ) as cur:
            count = (await cur.fetchone())[0]
        if count >= 6:
            return False  # Team is full, send to storage
        slot = count + 1
        await db.execute(
            """INSERT INTO team (discord_id, pokemon_id, current_hp, max_hp, level, slot)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (discord_id, pokemon_id, max_hp, max_hp, level, slot)
        )
        await db.commit()
        return True


async def update_team_pokemon_hp(discord_id: str, slot: int, new_hp: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE team SET current_hp = MAX(0, ?) WHERE discord_id = ? AND slot = ?",
            (new_hp, discord_id, slot)
        )
        await db.commit()


async def heal_all_team(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE team SET current_hp = max_hp WHERE discord_id = ?",
            (discord_id,)
        )
        await db.commit()


async def heal_team_with_potion(discord_id: str, slot: int, heal_amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE team SET current_hp = MIN(max_hp, current_hp + ?)
               WHERE discord_id = ? AND slot = ?""",
            (heal_amount, discord_id, slot)
        )
        await db.commit()


# ============================================================
# STORAGE
# ============================================================

async def get_storage(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM storage WHERE discord_id = ?", (discord_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def add_to_storage(discord_id: str, pokemon_id: int, max_hp: int, level: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO storage (discord_id, pokemon_id, current_hp, max_hp, level) VALUES (?, ?, ?, ?, ?)",
            (discord_id, pokemon_id, max_hp, max_hp, level)
        )
        await db.commit()


# ============================================================
# INVENTORY
# ============================================================

async def get_inventory(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM inventory WHERE discord_id = ? AND quantity > 0",
            (discord_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_item_quantity(discord_id: str, item_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT quantity FROM inventory WHERE discord_id = ? AND item_name = ?",
            (discord_id, item_name)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def add_item(discord_id: str, item_name: str, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO inventory (discord_id, item_name, quantity)
               VALUES (?, ?, ?)
               ON CONFLICT(discord_id, item_name)
               DO UPDATE SET quantity = quantity + ?""",
            (discord_id, item_name, quantity, quantity)
        )
        await db.commit()


async def remove_item(discord_id: str, item_name: str, quantity: int = 1) -> bool:
    """מסיר פריט. מחזיר False אם אין מספיק."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT quantity FROM inventory WHERE discord_id = ? AND item_name = ?",
            (discord_id, item_name)
        ) as cur:
            row = await cur.fetchone()
            if not row or row[0] < quantity:
                return False
        await db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE discord_id = ? AND item_name = ?",
            (quantity, discord_id, item_name)
        )
        await db.commit()
        return True


# ============================================================
# ZONE
# ============================================================

async def get_zone(discord_id: str) -> str:
    """מחזיר את האזור הנוכחי של השחקן"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT current_zone FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else "grass"


async def set_zone(discord_id: str, zone: str):
    """מגדיר את אזור הסיור של השחקן"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET current_zone = ? WHERE discord_id = ?",
            (zone, discord_id)
        )
        await db.commit()


# ============================================================
# XP / LEVEL / EVOLUTION
# ============================================================

def _exp_to_next(level: int) -> int:
    """XP הדרוש לרמה הבאה"""
    return int(100 * (1.2 ** (level - 1)))


async def give_exp_and_check_levelup(
    discord_id: str, slot: int, exp_gained: int
) -> dict:
    """
    מעניק XP לפוקימון ובודק Level Up ואבולוציה.
    מחזיר dict עם: leveled_up, new_level, evolved_to, old_pokemon_id
    """
    from config import EVOLUTION_TABLE

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM team WHERE discord_id = ? AND slot = ?",
            (discord_id, slot)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return {"leveled_up": False, "new_level": 1, "evolved_to": None, "old_pokemon_id": 0}
            entry = dict(row)

        cur_exp = (entry.get("exp") or 0) + exp_gained
        cur_level = entry.get("level") or 5
        leveled_up = False
        evolved_to = None
        old_pid = entry["pokemon_id"]
        cur_pid = old_pid

        # Level-Up loop (can gain multiple levels at once)
        while cur_exp >= _exp_to_next(cur_level):
            cur_exp -= _exp_to_next(cur_level)
            cur_level += 1
            leveled_up = True

            # Check evolution for the current pokemon_id
            evo = EVOLUTION_TABLE.get(cur_pid)
            if evo and evo[0] is not None and cur_level >= evo[1]:
                evolved_to = evo[0]
                cur_pid = evolved_to  # track for chain evolutions

        await db.execute(
            """UPDATE team SET exp = ?, level = ?, pokemon_id = ?
               WHERE discord_id = ? AND slot = ?""",
            (cur_exp, cur_level, cur_pid, discord_id, slot)
        )
        await db.commit()

        return {
            "leveled_up": leveled_up,
            "new_level": cur_level,
            "evolved_to": evolved_to,
            "old_pokemon_id": old_pid,
        }
