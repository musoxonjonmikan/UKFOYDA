import os
import logging
from pymongo import MongoClient

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    ContextTypes,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["DATABASE_URL"]

client = MongoClient(MONGO_URI)
db = client["bot_db"]

users = db["users"]
joins = db["joins"]

CHANNEL_1_USERNAME = "@ucplanet"
CHANNEL_2_ID = -1003934812939
CHANNEL_3_ID = -1003999645745
PRIZE_CHANNEL_ID = -1003822385223

BOT_USERNAME = "ucfoydabot"
ADMIN_ID = 5523761749
REQUIRED_INVITES = 2

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── DB FUNCTIONS (MONGO) ─────────────────────────────────────────────────────

def upsert_user(uid, username, first_name, invited_by=None):
    users.update_one(
        {"telegram_id": uid},
        {
            "$set": {"username": username, "first_name": first_name},
            "$setOnInsert": {
                "telegram_id": uid,
                "referral_count": 0,
                "is_verified": False,
                "join_link_sent": False,
                "invited_by": invited_by,
            }
        },
        upsert=True
    )

def get_user(uid):
    return users.find_one({"telegram_id": uid})

def set_verified(uid):
    users.update_one({"telegram_id": uid}, {"$set": {"is_verified": True}})

def inc_ref(uid):
    r = users.find_one_and_update(
        {"telegram_id": uid},
        {"$inc": {"referral_count": 1}},
        return_document=True
    )
    return r.get("referral_count", 0)

def has_join(uid, chat_id):
    return joins.find_one({"user_id": uid, "chat_id": chat_id}) is not None

def add_join(uid, chat_id):
    joins.update_one(
        {"user_id": uid, "chat_id": chat_id},
        {"$setOnInsert": {"user_id": uid, "chat_id": chat_id}},
        upsert=True
    )

# ─── KEYBOARD ────────────────────────────────────────────────────────────────

def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join 1", url="https://t.me/ucplanet")],
        [InlineKeyboardButton("Join 2", url="https://t.me/+link2")],
        [InlineKeyboardButton("Join 3", url="https://t.me/+link3")],
        [InlineKeyboardButton("Check", callback_data="check")]
    ])

# ─── HANDLERS ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name)

    await update.message.reply_text(
        "Welcome to contest",
        reply_markup=kb()
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    u = q.from_user
    user = get_user(u.id)

    if not user:
        return

    ch2 = has_join(u.id, CHANNEL_2_ID)
    ch3 = has_join(u.id, CHANNEL_3_ID)

    if not (ch2 and ch3):
        await q.message.reply_text("Join all channels first")
        return

    set_verified(u.id)

    await q.message.reply_text("Verified!")

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = update.chat_join_request
    add_join(r.from_user.id, r.chat.id)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check, pattern="check"))
    app.add_handler(ChatJoinRequestHandler(join_request))

    logger.info("Bot running (polling)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
