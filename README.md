# 🎮 Pokémon Discord Bot

בוט דיסקורד לפוקימון בפייתון — ממוחזר מהמשחק המקורי.
שחקנים משחקים **ישירות דרך הצ'אט** עם **ריאקציות-אימוגים**!

## ✨ פיצ'רים

- ⚔️ **קרבות turn-based** — בחר מהלכים עם 1️⃣2️⃣3️⃣4️⃣
- 🔴 **תפיסת פוקימונים** — זרוק Poké Ball באמצע קרב
- 👤 **פרופיל עם שישייה** — עד 6 פוקימונים בצוות
- 🏪 **חנות** — קנה כדורים ותרופות עם Silver
- 🎒 **מלאי** — השתמש בתרופות בכל עת
- 🏥 **מרכז רפואה** — רפא את כל הצוות חינם
- 📖 **פוקידקס** — מידע על 151 פוקימון
- 📦 **אחסון** — פוקימונים נוספים נשמרים בקופסה

## 🚀 התקנה

### 1. התקן תלויות
```bash
cd pokemon-discord-bot
pip install -r requirements.txt
```

### 2. צור בוט בדיסקורד
1. כנס ל-[Discord Developer Portal](https://discord.com/developers/applications)
2. צור **New Application**
3. לך ל-**Bot** → **Add Bot**
4. העתק את **Token**
5. אפשר: `MESSAGE CONTENT INTENT`, `SERVER MEMBERS INTENT`, `PRESENCE INTENT`

### 3. הגדר את ה-Token
ערוך את קובץ `.env`:
```
DISCORD_TOKEN=הכנס_כאן_את_הטוקן_שלך
```

### 4. הוסף את הבוט לשרת
בהגדרות הבוט → OAuth2 → URL Generator:
- Scopes: `bot`
- Permissions: `Send Messages`, `Add Reactions`, `Embed Links`, `Read Message History`

העתק את ה-URL ופתח בדפדפן.

### 5. הפעל את הבוט
```bash
python bot.py
```

## 🎮 פקודות

| פקודה | תיאור |
|-------|-------|
| `!start` | התחל את המשחק ובחר פוקימון ראשוני |
| `!battle` | קרב עם פוקימון פראי אקראי |
| `!profile` | ראה את הפרופיל שלך |
| `!team` | ראה את השישייה המפורטת |
| `!store` | פתח את החנות |
| `!buy <פריט>` | קנה פריט |
| `!inventory` | ראה את המלאי |
| `!use <פריט>` | השתמש בתרופה |
| `!heal` | רפא את כל הצוות (חינם) |
| `!pokedex <שם>` | מידע על פוקימון |
| `!storage` | ראה את האחסון |
| `!help` | רשימת כל הפקודות |

## ⚔️ איך מנצחים?

1. **!start** — בחר Bulbasaur/Charmander/Squirtle עם 1️⃣/2️⃣/3️⃣
2. **!battle** — קרב מתחיל! בחר מהלך עם ריאקציה
3. נצח → קבל **Silver** ו-**EXP**
4. תפוס פוקימונים עם 5️⃣ בקרב (בחר כדור)
5. קנה ציוד עם `!store` + `!buy`
6. רפא עם `!heal` כשהצוות חלש

## 📁 מבנה קבצים

```
pokemon-discord-bot/
├── bot.py               # נקודת כניסה
├── config.py            # הגדרות
├── .env                 # טוקן (אל תשתף!)
├── requirements.txt
├── data/
│   └── pokemon_data.json  # 151 פוקימונים
├── database/
│   └── db.py            # SQLite
├── cogs/                # מודולי פקודות
│   ├── starter.py
│   ├── battle.py
│   ├── profile.py
│   ├── store.py
│   ├── inventory.py
│   └── healing.py
└── utils/               # פונקציות עזר
    ├── pokemon_utils.py
    ├── battle_utils.py
    └── embed_utils.py
```
