import os
import json
import logging
import requests
from datetime import datetime, time as dtime

import pytz
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ----------------— CONFIGURATION —----------------

# استخدم متغير بيئي أو أدخل التوكن مباشرة هنا للاختبار
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN",
                       "8028036634:AAFS_FjnPrzLw1B-qYp2l1VCoYJBcRcXiv8")

USER_DATA_FILE = "user_data.json"
ARABIC = "ar"
ENGLISH = "en"
DEFAULT_LANG = ARABIC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------— DATA HELPERS —----------------

def load_data() -> dict:
    """Load user data from JSON file."""
    if not os.path.isfile(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_data(data: dict):
    """Save user data to JSON file."""
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def symbol_to_id(symbol: str) -> str | None:
    """Map ticker symbol to CoinGecko ID."""
    mapping = {
        "sol": "solana",
        "link": "chainlink",
        "xrp": "ripple",
        # أضف المزيد حسب الحاجة
    }
    return mapping.get(symbol.lower())


def get_price(symbol_id: str) -> float:
    """Fetch current USD price from CoinGecko."""
    if not symbol_id:
        return 0.0

    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={symbol_id}&vs_currencies=usd"
    )
    try:
        resp = requests.get(url, timeout=10)
        return resp.json().get(symbol_id, {}).get("usd", 0.0)
    except Exception as e:
        logger.warning(f"Error fetching price for {symbol_id}: {e}")
        return 0.0


def local_time_now() -> str:
    """Return current time in Africa/Tunis timezone."""
    tz = pytz.timezone("Africa/Tunis")
    return datetime.now(tz).strftime("%H:%M:%S")


def get_msg(key: str, lang: str) -> str:
    """Retrieve a localized message."""
    messages = {
        "start": {
            ARABIC: "👋 مرحبًا بك في بوت متابعة العملات الرقمية!",
            ENGLISH: "👋 Welcome to the crypto tracking bot!",
        },
        "help": {
            ARABIC: (
                "/addcoin - إضافة عملة\n"
                "/removecoin - حذف عملة\n"
                "/stats - عرض حالتك\n"
                "/news - عرض الأخبار\n"
                "/lang - تغيير اللغة\n"
                "/help - قائمة الأوامر"
            ),
            ENGLISH: (
                "/addcoin - Add coin\n"
                "/removecoin - Remove coin\n"
                "/stats - Portfolio status\n"
                "/news - Show news\n"
                "/lang - Change language\n"
                "/help - Commands list"
            ),
        },
        "no_coins": {
            ARABIC: "⚠️ لم تقم بإضافة أي عملة بعد.",
            ENGLISH: "⚠️ You haven't added any coins yet.",
        },
    }
    return messages.get(key, {}).get(lang, "")


# ----------------— COMMAND HANDLERS —----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"coins": [], "lang": DEFAULT_LANG}
        save_data(data)
    await update.message.reply_text(get_msg("start", data[user_id]["lang"]))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    lang = data.get(user_id, {}).get("lang", DEFAULT_LANG)
    await update.message.reply_text(get_msg("help", lang))


async def addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {"coins": [], "lang": DEFAULT_LANG}

    try:
        symbol, amount, price = context.args
        symbol = symbol.lower()
        coin = {
            "symbol": symbol,
            "amount": float(amount),
            "price": float(price)
        }
        data[user_id]["coins"].append(coin)
        save_data(data)
        await update.message.reply_text(f"✅ تمت إضافة {symbol.upper()} بنجاح.")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ الصيغة: /addcoin رمز الكمية السعر")


async def removecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    symbol = context.args[0].lower() if context.args else ""
    data = load_data()
    coins = data.get(user_id, {}).get("coins", [])
    data[user_id]["coins"] = [c for c in coins if c["symbol"] != symbol]
    save_data(data)
    await update.message.reply_text(f"🗑️ تم حذف {symbol.upper()}.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = data.get(user_id)

    if not user_data or not user_data["coins"]:
        await update.message.reply_text(get_msg("no_coins", DEFAULT_LANG))
        return

    reply = "📊 حالتك:\n"
    for coin in user_data["coins"]:
        sid = symbol_to_id(coin["symbol"])
        current_price = get_price(sid)
        percent = ((current_price - coin["price"]) / coin["price"]) * 100
        reply += f"- {coin['symbol'].upper()}: {percent:.2f}%\n"

    await update.message.reply_text(reply)


async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    current = data.get(user_id, {}).get("lang", DEFAULT_LANG)
    new_lang = ENGLISH if current == ARABIC else ARABIC
    data[user_id]["lang"] = new_lang
    save_data(data)
    await update.message.reply_text(
        "✅ Language updated." if new_lang == ENGLISH else "✅ تم تغيير اللغة."
    )


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    coins = data.get(user_id, {}).get("coins", [])

    if not coins:
        await update.message.reply_text(get_msg("no_coins", DEFAULT_LANG))
        return

    reply = "📰 آخر الأخبار:\n"
    for coin in coins:
        reply += f"- {coin['symbol'].upper()}: لا توجد أخبار حالياً\n"
    await update.message.reply_text(reply)


# ----------------— DAILY NOTIFICATIONS —----------------

async def send_daily_notifications(context: ContextTypes.DEFAULT_TYPE):
    """This job runs every day at 20:00 تونس."""
    data = load_data()
    for user_id, info in data.items():
        coins = info.get("coins", [])
        if not coins:
            continue

        text = f"⏰ {local_time_now()} - إشعار يومي:\n"
        for coin in coins:
            sid = symbol_to_id(coin["symbol"])
            price = get_price(sid)
            percent = ((price - coin["price"]) / coin["price"]) * 100
            status = (
                "📈 ربح" if percent >= 20
                else "📉 خسارة" if percent <= -10
                else "ℹ️"
            )
            text += f"{coin['symbol'].upper()}: {price}$ ({percent:.2f}%) {status}\n"

        await context.bot.send_message(chat_id=int(user_id), text=text)


# ----------------— MAIN ENTRYPOINT —----------------

def main():
    app = Application.builder().token(TOKEN).build()

    # register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addcoin", addcoin))
    app.add_handler(CommandHandler("removecoin", removecoin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("lang", lang))
    app.add_handler(CommandHandler("news", news))

    # schedule daily job at 20:00 Africa/Tunis
    tz = pytz.timezone("Africa/Tunis")
    app.job_queue.run_daily(
        send_daily_notifications,
        time=dtime(hour=20, minute=0, tzinfo=tz),
    )

    # this call will block and run the bot
    app.run_polling()


if __name__ == "__main__":
    main()
