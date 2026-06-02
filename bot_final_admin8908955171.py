import os
import asyncio
import sqlite3
from datetime import datetime
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================
# Hosting/Koyeb/Render e Environment Variables set korben:
# BOT_TOKEN=8955538835:AAFQ0BVY5zJCDRfxT222NVg0SyHREa8mFAY
# ADMIN_ID=7509920532
# FORCE_JOIN_CHANNEL=@yourchannel  OR  -1001234567890
# REF_BONUS=5
# ORDER_COST=20
# PAYMENT_BINANCE_ID=850566283

TOKEN = os.getenv("8955538835:AAFQ0BVY5zJCDRfxT222NVg0SyHREa8mFAY", "CHANGE_ME")
ADMIN_ID = 8908955171
# Multiple force-join channels/groups.
# Public channels/groups can be checked by @username.
# Private invite links cannot be checked by Telegram API directly; use numeric chat_id after adding bot.
FORCE_JOIN_TARGETS = [
    {"chat": "@gemini_pixel_vr", "title": "Gemini Pixel VR", "url": "https://t.me/gemini_pixel_vr", "check": True},
    {"chat": "@free_internet_config_bd", "title": "Free Internet Config BD", "url": "https://t.me/free_internet_config_bd", "check": True},
    {"chat": "@gemini_vr_Chat", "title": "Gemini VR Chat", "url": "https://t.me/gemini_vr_Chat", "check": True},
]
REF_BONUS = 1
ORDER_COST = 10
PAYMENT_BINANCE_ID = os.getenv("PAYMENT_BINANCE_ID", "850566283")

DB_PATH = os.getenv("DB_PATH", "bot.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

# =========================
# DATABASE
# =========================
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 0,
        language TEXT DEFAULT 'en',
        referred_by INTEGER DEFAULT NULL,
        referral_count INTEGER DEFAULT 0,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
)
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        details TEXT,
        status TEXT,
        result TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
)
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        package_coins INTEGER,
        trx_id TEXT UNIQUE,
        screenshot_file_id TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """
)
conn.commit()

# Safe migration for older bot.db
for sql in [
    "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'",
    "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
    "ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN joined_at TEXT DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE orders ADD COLUMN result TEXT DEFAULT ''",
    "ALTER TABLE orders ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP",
]:
    try:
        cur.execute(sql)
        conn.commit()
    except Exception:
        pass

# Force all existing users to English by default
# Remove/comment these 3 lines later if you want users' selected languages to stay saved.
cur.execute("UPDATE users SET language = 'en'")
conn.commit()

# =========================
# LANGUAGE TEXT
# =========================
LANGS = {
    "en": "English",
    "bn": "বাংলা",
    "ur": "اردو",
    "hi": "हिन्दी",
}

T = {
    "choose_lang": {
        "en": "🌐 Please choose your language:",
        "bn": "🌐 আপনার ভাষা নির্বাচন করুন:",
        "ur": "🌐 اپنی زبان منتخب کریں:",
        "hi": "🌐 अपनी भाषा चुनें:",
    },
    "welcome": {
        "en": "Welcome ✅\nSelect an option from the menu.",
        "bn": "স্বাগতম ✅\nMenu থেকে option select করুন।",
        "ur": "خوش آمدید ✅\nMenu سے option منتخب کریں۔",
        "hi": "स्वागत है ✅\nMenu से option select करें।",
    },
    "force_join": {
        "en": "🔒 To use this bot, please join all required channels/groups first, then press Check Joined.",
        "bn": "🔒 Bot ব্যবহার করতে আগে সব required channel/group join করুন, তারপর Check Joined চাপুন।",
        "ur": "🔒 Bot استعمال کرنے کے لیے پہلے تمام required channel/group join کریں، پھر Check Joined دبائیں۔",
        "hi": "🔒 Bot use करने के लिए पहले सभी required channel/group join करें, फिर Check Joined दबाएं।",
    },
    "joined_ok": {"en": "✅ Verified!", "bn": "✅ Verified!", "ur": "✅ Verified!", "hi": "✅ Verified!"},
    "not_joined": {
        "en": "❌ You have not joined yet.",
        "bn": "❌ আপনি এখনো join করেননি।",
        "ur": "❌ آپ نے ابھی join نہیں کیا۔",
        "hi": "❌ आपने अभी join नहीं किया।",
    },
    "balance": {
        "en": "💰 Your balance: {coins} coins",
        "bn": "💰 আপনার balance: {coins} coins",
        "ur": "💰 آپ کا balance: {coins} coins",
        "hi": "💰 आपका balance: {coins} coins",
    },
    "low_balance": {
        "en": "❌ Low balance. Please buy coins first.",
        "bn": "❌ আপনার balance কম। আগে coins কিনুন।",
        "ur": "❌ Balance کم ہے۔ پہلے coins خریدیں۔",
        "hi": "❌ Balance कम है। पहले coins खरीदें।",
    },
    "buy_coins": {
        "en": "💳 Buy Coins\n\n🟡 Binance ID: {binance}\n\nPackages:\n10 Coins = 1 USDT\n50 Coins = 5 USDT\n100 Coins = 10 USDT\n\nNow choose package below.",
        "bn": "💳 Coins কিনতে payment করুন\n\n🟡 Binance ID: {binance}\n\nPackages:\n10 Coins = 1 USDT\n50 Coins = 5 USDT\n100 Coins = 10 USDT\n\nএখন নিচ থেকে package select করুন।",
        "ur": "💳 Coins خریدیں\n\n🟡 Binance ID: {binance}\n\nPackages:\n10 Coins = 1 USDT\n50 Coins = 5 USDT\n100 Coins = 10 USDT\n\nاب نیچے سے package منتخب کریں۔",
        "hi": "💳 Coins खरीदें\n\n🟡 Binance ID: {binance}\n\nPackages:\n10 Coins = 1 USDT\n50 Coins = 5 USDT\n100 Coins = 10 USDT\n\nअब नीचे से package select करें।",
    },
    "send_trx": {
        "en": "✅ Package selected: {coins} coins\n\nNow send only your Order ID.\nScreenshot optional: you can send screenshot after Order ID.",
        "bn": "✅ Package selected: {coins} coins\n\nএখন শুধু Order ID পাঠান।\nScreenshot optional: Order ID দেওয়ার পর screenshot পাঠাতে পারেন।",
        "ur": "✅ Package selected: {coins} coins\n\nاب Order ID بھیجیں۔\nScreenshot optional ہے۔",
        "hi": "✅ Package selected: {coins} coins\n\nअब Order ID भेजें।\nScreenshot optional है।",
    },
    "payment_pending": {
        "en": "✅ Payment request submitted. Admin will verify Order ID.",
        "bn": "✅ Payment request submitted. Admin Order ID verify করবে।",
        "ur": "✅ Payment request submitted. Admin Order ID verify کرے گا۔",
        "hi": "✅ Payment request submitted. Admin Order ID verify करेगा।",
    },
    "new_order_prompt": {
        "en": "📦 New Order\n💰 Cost: {cost} coins\n\nSend all details together:\n📧 Email:\n🔑 Password:\n🔐 2FA Code:",
        "bn": "📦 New Order\n💰 Cost: {cost} coins\n\nনিচের তথ্যগুলো একসাথে পাঠান:\n📧 Email:\n🔑 Password:\n🔐 2FA Code:",
        "ur": "📦 New Order\n💰 Cost: {cost} coins\n\nتمام details ایک ساتھ بھیجیں:\n📧 Email:\n🔑 Password:\n🔐 2FA Code:",
        "hi": "📦 New Order\n💰 Cost: {cost} coins\n\nसारी details एक साथ भेजें:\n📧 Email:\n🔑 Password:\n🔐 2FA Code:",
    },
    "ref": {
        "en": "👥 Your referral link:\n{link}\n\nBonus: {bonus} coins per valid referral.\nTotal referrals: {count}",
        "bn": "👥 আপনার referral link:\n{link}\n\nBonus: প্রতি valid referral এ {bonus} coins।\nTotal referrals: {count}",
        "ur": "👥 آپ کا referral link:\n{link}\n\nBonus: ہر valid referral پر {bonus} coins۔\nTotal referrals: {count}",
        "hi": "👥 आपका referral link:\n{link}\n\nBonus: हर valid referral पर {bonus} coins।\nTotal referrals: {count}",
    },
}

MENU_TEXTS = {
    "balance": {"en": "💰 Balance", "bn": "💰 Balance", "ur": "💰 Balance", "hi": "💰 Balance"},
    "buy": {"en": "💳 Buy Coins", "bn": "💳 Buy Coins", "ur": "💳 Buy Coins", "hi": "💳 Buy Coins"},
    "order": {"en": "📦 New Order", "bn": "📦 New Order", "ur": "📦 New Order", "hi": "📦 New Order"},
    "myorders": {"en": "📜 My Orders", "bn": "📜 My Orders", "ur": "📜 My Orders", "hi": "📜 My Orders"},
    "referral": {"en": "👥 Referral", "bn": "👥 Referral", "ur": "👥 Referral", "hi": "👥 Referral"},
    "language": {"en": "🌐 Language", "bn": "🌐 Language", "ur": "🌐 Language", "hi": "🌐 Language"},
    "admin": {"en": "🛠 Admin Panel", "bn": "🛠 Admin Panel", "ur": "🛠 Admin Panel", "hi": "🛠 Admin Panel"},
}


def tr(key: str, lang: str = "en", **kwargs) -> str:
    lang = lang if lang in LANGS else "en"
    return T[key][lang].format(**kwargs)


def get_lang(user_id: int) -> str:
    cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return (row[0] if row and row[0] else "en")


def main_menu(user_id: int) -> ReplyKeyboardMarkup:
    lang = get_lang(user_id)
    rows = [
        [MENU_TEXTS["balance"][lang], MENU_TEXTS["buy"][lang]],
        [MENU_TEXTS["order"][lang], MENU_TEXTS["myorders"][lang]],
        [MENU_TEXTS["referral"][lang], MENU_TEXTS["language"][lang]],
    ]
    if user_id == ADMIN_ID:
        rows.append([MENU_TEXTS["admin"][lang]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data="lang_en"), InlineKeyboardButton("বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("اردو", callback_data="lang_ur"), InlineKeyboardButton("हिन्दी", callback_data="lang_hi")],
    ])


def force_join_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for target in FORCE_JOIN_TARGETS:
        rows.append([InlineKeyboardButton(f"📢 Join {target['title']}", url=target["url"])])
    rows.append([InlineKeyboardButton("✅ Check Joined", callback_data="check_joined")])
    return InlineKeyboardMarkup(rows)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"), InlineKeyboardButton("💳 Pending Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("📦 Pending Orders", callback_data="admin_orders")],
    ])


def payment_package_keyboard() -> InlineKeyboardMarkup:
    amounts = list(range(10, 111, 10))
    rows = []
    for i in range(0, len(amounts), 3):
        rows.append([
            InlineKeyboardButton(f"{coin} Coins", callback_data=f"pkg_{coin}")
            for coin in amounts[i:i+3]
        ])
    return InlineKeyboardMarkup(rows)


def register_user(user, referred_by: Optional[int] = None) -> bool:
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
    exists = cur.fetchone()
    if exists:
        cur.execute("UPDATE users SET username = ? WHERE user_id = ?", (user.username or "No username", user.id))
        conn.commit()
        return False

    valid_ref = referred_by if referred_by and referred_by != user.id else None
    cur.execute(
        "INSERT INTO users (user_id, username, coins, language, referred_by) VALUES (?, ?, 0, 'en', ?)",
        (user.id, user.username or "No username", valid_ref),
    )
    if valid_ref:
        cur.execute("UPDATE users SET coins = coins + ?, referral_count = referral_count + 1 WHERE user_id = ?", (REF_BONUS, valid_ref))
    conn.commit()
    return True


async def is_joined(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True only if user joined every checkable force-join target."""
    if user_id == ADMIN_ID:
        return True

    for target in FORCE_JOIN_TARGETS:
        if not target.get("check"):
            # Invite-link-only private groups cannot be verified without numeric chat_id.
            continue

        chat_id = target.get("chat")
        if not chat_id:
            continue

        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except (BadRequest, Forbidden):
            return False
        except Exception:
            return False

    return True


async def require_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    if await is_joined(user_id, context):
        return True
    text = tr("force_join", lang)
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=force_join_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=force_join_keyboard())
    return False

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    referred_by = None
    if context.args:
        try:
            if context.args[0].startswith("ref_"):
                referred_by = int(context.args[0].split("_", 1)[1])
        except Exception:
            referred_by = None

    is_new = register_user(update.effective_user, referred_by)
    lang = get_lang(update.effective_user.id)

    if is_new and referred_by:
        try:
            await context.bot.send_message(referred_by, f"🎉 New referral joined! +{REF_BONUS} coins added.")
        except Exception:
            pass

    if not await require_join(update, context):
        return

    await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_keyboard())
    await update.message.reply_text(tr("welcome", lang), reply_markup=main_menu(update.effective_user.id))


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")


async def addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except Exception:
        await update.message.reply_text("Use: /addcoin user_id amount")
        return

    cur.execute("INSERT OR IGNORE INTO users (user_id, username, coins, language) VALUES (?, ?, 0, 'bn')", (user_id, "Unknown"))
    cur.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    await update.message.reply_text(f"✅ {amount} coins added to {user_id}.")
    try:
        await context.bot.send_message(user_id, f"✅ Your account received {amount} coins.")
    except Exception:
        pass


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        order_id = int(context.args[0])
        result_text = " ".join(context.args[1:]).strip()
        if not result_text:
            raise ValueError
    except Exception:
        await update.message.reply_text("Use: /result order_id result_text")
        return

    cur.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text("Order not found.")
        return

    user_id = row[0]
    cur.execute("UPDATE orders SET status = ?, result = ? WHERE id = ?", ("Done", result_text, order_id))
    conn.commit()

    parts = result_text.split("|", 1)
    main_result = parts[0].strip()
    link = parts[1].strip() if len(parts) > 1 else ""
    msg = f"✅ Your Order #{order_id} completed.\n\n📄 Result:\n{main_result}"
    if link:
        msg += f"\n\n🔗 Copy Link:\n{link}"

    await context.bot.send_message(user_id, msg)
    await update.message.reply_text(f"✅ Result sent to Order #{order_id}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args).strip()
    if not msg:
        await update.message.reply_text("Use: /broadcast message")
        return
    cur.execute("SELECT user_id FROM users")
    users = [r[0] for r in cur.fetchall()]
    ok = fail = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, msg)
            ok += 1
        except Exception:
            fail += 1
    await update.message.reply_text(f"✅ Broadcast done. Sent: {ok}, Failed: {fail}")


async def pendingpayments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cur.execute("SELECT id, user_id, username, package_coins, trx_id FROM payments WHERE status = 'Pending' ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("No pending payments.")
        return

    for pid, uid, uname, coins, trx in rows:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Approve {coins}", callback_data=f"payapprove_{pid}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"payreject_{pid}")]
        ])
        await update.message.reply_text(
            f"💳 Payment #{pid}\nUser: {uid} @{uname}\nPackage: {coins} coins\nOrder ID: {trx}",
            reply_markup=kb
        )


# =========================
# MESSAGE HANDLERS
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    register_user(user)
    lang = get_lang(user.id)

    if not await require_join(update, context):
        return

    # Payment Order ID waiting
    if context.user_data.get("waiting_trx"):
        package_coins = int(context.user_data.get("payment_package", 0))
        trx_id = text.strip()
        if len(trx_id) < 4:
            await update.message.reply_text("❌ Order ID is too short. Please send valid ID.")
            return
        try:
            cur.execute(
                "INSERT INTO payments (user_id, username, package_coins, trx_id, status) VALUES (?, ?, ?, ?, 'Pending')",
                (user.id, user.username or "No username", package_coins, trx_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ This Order ID already submitted.")
            return

        payment_id = cur.lastrowid
        context.user_data["last_payment_id"] = payment_id
        context.user_data["waiting_trx"] = False
        context.user_data["waiting_payment_screenshot"] = True

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Approve {package_coins}", callback_data=f"payapprove_{payment_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"payreject_{payment_id}")],
        ])
        await update.message.reply_text(tr("payment_pending", lang) + "\n\n📸 Screenshot optional: send now if you want.")

        admin_msg = (
            f"💳 New Payment Request #{payment_id}\n"
            f"User ID: {user.id}\n"
            f"Username: @{user.username or 'No username'}\n"
            f"Package: {package_coins} coins\n"
            f"Order ID: {trx_id}\n"
            f"Status: Pending"
        )
        try:
            await context.bot.send_message(ADMIN_ID, admin_msg, reply_markup=buttons)
        except Exception as e:
            print("ADMIN PAYMENT NOTIFY ERROR:", repr(e))
            await update.message.reply_text("⚠️ Payment saved, but admin notification failed. Please contact admin.")

        return

    # New order waiting
    if context.user_data.get("waiting_order"):
        cur.execute("SELECT coins FROM users WHERE user_id = ?", (user.id,))
        coins = cur.fetchone()[0]
        if coins < ORDER_COST:
            await update.message.reply_text(tr("low_balance", lang))
            context.user_data["waiting_order"] = False
            return

        cur.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (ORDER_COST, user.id))
        cur.execute(
            "INSERT INTO orders (user_id, username, details, status) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "No username", text, "Pending"),
        )
        conn.commit()
        order_id = cur.lastrowid
        context.user_data["waiting_order"] = False

        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data=f"done_{order_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{order_id}")]])
        await update.message.reply_text(f"✅ Order placed!\nOrder ID: {order_id}\nStatus: Pending")
        await context.bot.send_message(
            ADMIN_ID,
            f"📦 New Order #{order_id}\nUser ID: {user.id}\nUsername: @{user.username}\nCost: {ORDER_COST} coins\n\nDetails:\n{text}",
            reply_markup=buttons,
        )
        return

    all_menu_values = {v[lang]: k for k, v in MENU_TEXTS.items()}
    action = all_menu_values.get(text)

    if action == "balance":
        cur.execute("SELECT coins FROM users WHERE user_id = ?", (user.id,))
        coins = cur.fetchone()[0]
        await update.message.reply_text(tr("balance", lang, coins=coins))

    elif action == "buy":
        await update.message.reply_text(tr("buy_coins", lang, binance=PAYMENT_BINANCE_ID), reply_markup=payment_package_keyboard())

    elif action == "order":
        await update.message.reply_text(tr("new_order_prompt", lang, cost=ORDER_COST))
        context.user_data["waiting_order"] = True

    elif action == "myorders":
        cur.execute("SELECT id, status, result FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user.id,))
        orders = cur.fetchall()
        if not orders:
            await update.message.reply_text("No orders found.")
        else:
            msg = "📜 Your Orders:\n\n"
            for oid, status, res in orders:
                msg += f"Order #{oid} - {status}\n"
                if res:
                    msg += f"Result: {res}\n"
                msg += "\n"
            await update.message.reply_text(msg)

    elif action == "referral":
        bot_username = (await context.bot.get_me()).username
        cur.execute("SELECT referral_count FROM users WHERE user_id = ?", (user.id,))
        count = cur.fetchone()[0]
        link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        await update.message.reply_text(tr("ref", lang, link=link, bonus=REF_BONUS, count=count))

    elif action == "language":
        await update.message.reply_text(tr("choose_lang", lang), reply_markup=lang_keyboard())

    elif action == "admin" and user.id == ADMIN_ID:
        await update.message.reply_text("🛠 Admin Panel", reply_markup=admin_panel_keyboard())

    else:
        await update.message.reply_text("Please choose an option from menu.", reply_markup=main_menu(user.id))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    lang = get_lang(user.id)

    if not await require_join(update, context):
        return

    file_id = update.message.photo[-1].file_id
    payment_id = context.user_data.get("last_payment_id")

    if context.user_data.get("waiting_payment_screenshot") and payment_id:
        cur.execute("UPDATE payments SET screenshot_file_id = ? WHERE id = ? AND user_id = ?", (file_id, payment_id, user.id))
        conn.commit()
        cur.execute("SELECT package_coins, trx_id FROM payments WHERE id = ?", (payment_id,))
        row = cur.fetchone()
        coins, trx_id = row if row else (0, "Unknown")
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Approve {coins}", callback_data=f"payapprove_{payment_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"payreject_{payment_id}")],
        ])
        await update.message.reply_text("✅ Screenshot received. Admin will verify.")
        await context.bot.send_photo(
            ADMIN_ID,
            photo=file_id,
            caption=f"💳 Payment Screenshot #{payment_id}\nUser ID: {user.id}\nUsername: @{user.username}\nPackage: {coins} coins\nOrder ID: {trx_id}",
            reply_markup=buttons,
        )
        context.user_data["waiting_payment_screenshot"] = False
        return

    await update.message.reply_text("📸 Screenshot received, but please select Buy Coins package and submit Order ID first.")

# =========================
# CALLBACKS
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("lang_"):
        lang = data.split("_", 1)[1]
        if lang in LANGS:
            cur.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
            conn.commit()
            await query.message.reply_text(f"✅ Language set: {LANGS[lang]}", reply_markup=main_menu(user_id))
        return

    if data == "check_joined":
        lang = get_lang(user_id)
        if await is_joined(user_id, context):
            await query.message.reply_text(tr("joined_ok", lang), reply_markup=main_menu(user_id))
        else:
            await query.message.reply_text(tr("not_joined", lang), reply_markup=force_join_keyboard())
        return

    if data.startswith("pkg_"):
        if not await require_join(update, context):
            return
        coins = int(data.split("_", 1)[1])
        context.user_data["payment_package"] = coins
        context.user_data["waiting_trx"] = True
        lang = get_lang(user_id)
        await query.message.reply_text(tr("send_trx", lang, coins=coins))
        return

    # Admin-only callbacks below
    if user_id != ADMIN_ID:
        await query.message.reply_text("আপনি admin নন।")
        return

    if data == "admin_stats":
        cur.execute("SELECT COUNT(*), COALESCE(SUM(coins), 0), COALESCE(SUM(referral_count), 0) FROM users")
        total_users, total_coins, total_refs = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
        pending_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pending'")
        pending_payments = cur.fetchone()[0]
        await query.message.reply_text(
            f"📊 Bot Stats\nUsers: {total_users}\nTotal Coins: {total_coins}\nTotal Referrals: {total_refs}\nPending Orders: {pending_orders}\nPending Payments: {pending_payments}"
        )
        return

    if data == "admin_payments":
        cur.execute("SELECT id, user_id, username, package_coins, trx_id FROM payments WHERE status = 'Pending' ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        if not rows:
            await query.message.reply_text("No pending payments.")
        for pid, uid, uname, coins, trx in rows:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Approve {coins}", callback_data=f"payapprove_{pid}"), InlineKeyboardButton("❌ Reject", callback_data=f"payreject_{pid}")]])
            await query.message.reply_text(f"💳 Payment #{pid}\nUser: {uid} @{uname}\nPackage: {coins}\nOrder ID: {trx}", reply_markup=kb)
        return

    if data == "admin_orders":
        cur.execute("SELECT id, user_id, username, details FROM orders WHERE status = 'Pending' ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        if not rows:
            await query.message.reply_text("No pending orders.")
        for oid, uid, uname, details in rows:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data=f"done_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{oid}")]])
            await query.message.reply_text(f"📦 Order #{oid}\nUser: {uid} @{uname}\nDetails:\n{details}", reply_markup=kb)
        return

    if data.startswith("payapprove_"):
        payment_id = int(data.split("_", 1)[1])
        cur.execute("SELECT user_id, package_coins, status FROM payments WHERE id = ?", (payment_id,))
        row = cur.fetchone()
        if not row:
            await query.message.reply_text("Payment not found.")
            return
        uid, coins, status = row
        if status != "Pending":
            await query.message.reply_text(f"Already {status}.")
            return
        cur.execute("UPDATE payments SET status = 'Approved' WHERE id = ?", (payment_id,))
        cur.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (coins, uid))
        conn.commit()
        await context.bot.send_message(uid, f"✅ Payment approved!\n{coins} coins added.")
        await query.message.reply_text(f"✅ Payment #{payment_id} approved. {coins} coins added to {uid}.")
        return

    if data.startswith("payreject_"):
        payment_id = int(data.split("_", 1)[1])
        cur.execute("SELECT user_id, status FROM payments WHERE id = ?", (payment_id,))
        row = cur.fetchone()
        if not row:
            await query.message.reply_text("Payment not found.")
            return
        uid, status = row
        if status != "Pending":
            await query.message.reply_text(f"Already {status}.")
            return
        cur.execute("UPDATE payments SET status = 'Rejected' WHERE id = ?", (payment_id,))
        conn.commit()
        await context.bot.send_message(uid, "❌ Payment rejected.")
        await query.message.reply_text(f"❌ Payment #{payment_id} rejected.")
        return

    if data.startswith("done_"):
        order_id = int(data.split("_")[1])
        cur.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        if not row:
            await query.message.reply_text("Order not found.")
            return
        uid = row[0]
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", ("Done", order_id))
        conn.commit()
        await context.bot.send_message(uid, f"✅ Your Order #{order_id} completed.")
        await query.message.reply_text(f"✅ Order #{order_id} marked as Done.")
        return

    if data.startswith("reject_order_"):
        order_id = int(data.split("_")[2])
        cur.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        if not row:
            await query.message.reply_text("Order not found.")
            return
        uid = row[0]
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", ("Rejected", order_id))
        cur.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (ORDER_COST, uid))
        conn.commit()
        await context.bot.send_message(uid, f"❌ Your Order #{order_id} rejected.\n{ORDER_COST} coins refunded.")
        await query.message.reply_text(f"❌ Order #{order_id} rejected and coins refunded.")
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("ERROR:", context.error)


def main():
    if TOKEN == "CHANGE_ME":
        raise RuntimeError("BOT_TOKEN environment variable set korun, or code e TOKEN boshan.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("addcoin", addcoin))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("pendingpayments", pendingpayments))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print(f"Custom Bot Started... ADMIN_ID={ADMIN_ID}, REF_BONUS={REF_BONUS}, ORDER_COST={ORDER_COST}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()
