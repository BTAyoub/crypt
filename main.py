import json
import requests
import logging
import schedule
import time
import pytz
import threading
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("8028036634:AAFS_FjnPrzLw1B-qYp2l1VCoYJBcRcXiv8")  # توكن البوت من متغير بيئي
USER_DATA_FILE = "user_data.json"
ARABIC = "ar"
ENGLISH = "en"
DEFAULT_LANG = ARABIC

# إعداد اللوج
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- أدوات ----------------

def load_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_price(symbol):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    response = requests.get(url)
    return response.json().get(symbol, {}).get("usd", 0)

def symbol_to_id(symbol):
    mapping = {
        "sol": "solana",
        "link": "chainlink",
        "xrp": "ripple"
    }
    return mapping.get(symbol.lower())

def local_time_now():
    return datetime.now(pytz.timezone("Africa/Tunis")).strftime("%H:%M:%S")

# ---------------- رسائل ----------------

def get_msg(key, lang):
    messages = {
        "start": {
            ARABIC: "👋 مرحبًا بك في بوت متابعة العملات الرقمية!",
            ENGLISH: "👋 Welcome to the crypto tracking bot!"
        },
        "help": {
            ARABIC: "/addcoin - إضافة عملة\n/removecoin - حذف عملة\n/stats - عرض حالتك\n/news - عرض الأخبار\n/lang - تغيير اللغة\n/help - قائمة الأوامر",
            ENGLISH: "/addcoin - Add coin\n/removecoin - Remove coin\n/stats - Portfolio status\n/news - Show news\n/lang - Change language\n/help - Commands list"
        },
        "no_coins": {
            ARABIC: "⚠️ لم تقم بإضافة أي عملة بعد.",
            ENGLISH: "⚠️ You haven't added any coins yet."
        },
    }
    return messages.get(key, {}).get(lang, "")

# ---------------- أوامر البوت ----------------

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
        coin = {"symbol": symbol, "amount": float(amount), "price": float(price)}
        data[user_id]["coins"].append(coin)
        save_data(data)
        await update.message.reply_text(f"✅ تمت إضافة {symbol.upper()} بنجاح.")
    except:
        await update.message.reply_text("❌ الصيغة: /addcoin رمز الكمية السعر")

async def removecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    symbol = context.args[0].lower() if context.args else ""
    data = load_data()
    coins = data.get(user_id, {}).get("coins", [])
    new_coins = [c for c in coins if c["symbol"] != symbol]
    data[user_id]["coins"] = new_coins
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
        current_price = get_price(symbol_to_id(coin["symbol"]))
        percent = ((current_price - coin["price"]) / coin["price"]) * 100
        reply += f"- {coin['symbol'].upper()}: {percent:.2f}%\n"
    await update.message.reply_text(reply)

async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    current_lang = data.get(user_id, {}).get("lang", DEFAULT_LANG)
    new_lang = ENGLISH if current_lang == ARABIC else ARABIC
    data[user_id]["lang"] = new_lang
    save_data(data)
    await update.message.reply_text("✅ Language updated." if new_lang == ENGLISH else "✅ تم تغيير اللغة.")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = data.get(user_id, {})
    coins = user_data.get("coins", [])
    if not coins:
        await update.message.reply_text(get_msg("no_coins", user_data.get("lang", DEFAULT_LANG)))
        return
    reply = "📰 آخر الأخبار:\n"
    for coin in coins:
        reply += f"- {coin['symbol'].upper()}: لا توجد أخبار حالياً\n"
    await update.message.reply_text(reply)

# ---------------- الإشعار التلقائي ----------------

async def send_daily_notifications(app):
    data = load_data()
    for user_id, info in data.items():
        coins = info.get("coins", [])
        if not coins:
            continue
        reply = f"⏰ {local_time_now()} - إشعار يومي:\n"
        for coin in coins:
            price = get_price(symbol_to_id(coin["symbol"]))
            percent = ((price - coin["price"]) / coin["price"]) * 100
            status = "📈 ربح" if percent >= 20 else "📉 خسارة" if percent <= -10 else "ℹ️"
            reply += f"{coin['symbol'].upper()}: {price}$ ({percent:.2f}%) {status}\n"
        try:
            await app.bot.send_message(chat_id=int(user_id), text=reply)
        except:
            continue

def schedule_loop(app):
    schedule.every().day.at("20:00").do(lambda: asyncio.run(send_daily_notifications(app)))
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---------------- تشغيل البوت ----------------

import asyncio

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addcoin", addcoin))
    app.add_handler(CommandHandler("removecoin", removecoin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("lang", lang))
    app.add_handler(CommandHandler("news", news))

    threading.Thread(target=schedule_loop, args=(app,), daemon=True).start()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
# محتوى main.py سيكون هو الكود الكامل للبوت الذي كتبناه مسبقًا
# سيتم وضعه تلقائيًا عند دمج المحتوى من المستند لاحقًا
