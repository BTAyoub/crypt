
import json
import logging
import os
import datetime
import requests
from flask import Flask
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "7963071210:AAGEHgS48YIbjHSCBehb6aYDM-vVvzKq7DE"
NEWS_API_KEY = "4e7fb52de4f44feca32a9110ecd1150f"
CRYPTOCOMPARE_API_KEY = "fd405453b43afbd4a8b7919d6dff0fe50fb0e584acc5cf858a1fa6e0c66f928a"

DATA_FILE = "data.json"

app = Flask(__name__)
bot = Bot(token=TOKEN)

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def get_user_data(user_id):
    data = load_data()
    return data.get(str(user_id), {"coins": [], "lang": "ar"})

def set_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    text = "مرحبا بك! أرسل /help لعرض الأوامر." if user_data["lang"] == "ar" else "Welcome! Send /help to see the commands."
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    if user_data["lang"] == "ar":
        text = "/stats - عرض حالة العملات\n/news - أخبار العملات\n/addcoin - إضافة عملة\n/lang - تغيير اللغة\n/help - المساعدة\n/removecoin - حذف عملة"
    else:
        text = "/stats - Show coin stats\n/news - Coin news\n/addcoin - Add a coin\n/lang - Change language\n/help - Help\n/removecoin - Remove a coin"
    await update.message.reply_text(text)

async def addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if len(context.args) != 2:
        await update.message.reply_text("اكتب /addcoin SYMBOL PRICE")
        return
    symbol = context.args[0].upper()
    try:
        price = float(context.args[1])
    except:
        await update.message.reply_text("السعر غير صحيح.")
        return
    user_data["coins"].append({"symbol": symbol, "buy_price": price})
    set_user_data(user_id, user_data)
    await update.message.reply_text(f"تمت إضافة {symbol}")

async def removecoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if len(context.args) != 1:
        await update.message.reply_text("اكتب /removecoin SYMBOL")
        return
    symbol = context.args[0].upper()
    user_data["coins"] = [c for c in user_data["coins"] if c["symbol"] != symbol]
    set_user_data(user_id, user_data)
    await update.message.reply_text(f"تم حذف {symbol}")

async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) != 1 or context.args[0] not in ["ar", "en"]:
        await update.message.reply_text("اكتب /lang ar أو /lang en")
        return
    user_data = get_user_data(user_id)
    user_data["lang"] = context.args[0]
    set_user_data(user_id, user_data)
    await update.message.reply_text("تم تغيير اللغة." if context.args[0] == "ar" else "Language changed.")

def get_price(symbol):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USDT&api_key={CRYPTOCOMPARE_API_KEY}"
    res = requests.get(url)
    return res.json().get("USDT")

def fetch_news():
    url = f"https://newsapi.org/v2/everything?q=crypto&apiKey={NEWS_API_KEY}"
    res = requests.get(url)
    articles = res.json().get("articles", [])[:3]
    return [f"{a['title']}\n{a['url']}" for a in articles]

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    msgs = []
    for coin in user_data["coins"]:
        price = get_price(coin["symbol"])
        if price:
            diff = price - coin["buy_price"]
            percent = (diff / coin["buy_price"]) * 100
            msg = f"{coin['symbol']}: {price} USDT\nالربح/الخسارة: {round(percent,2)}%"
            msgs.append(msg)
    await update.message.reply_text("\n\n".join(msgs) or "لا توجد عملات")

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    news_list = fetch_news()
    await update.message.reply_text("\n\n".join(news_list))

def daily_job():
    data = load_data()
    for user_id, user_data in data.items():
        msgs = []
        for coin in user_data["coins"]:
            price = get_price(coin["symbol"])
            if price:
                diff = price - coin["buy_price"]
                percent = (diff / coin["buy_price"]) * 100
                if percent >= 20 or percent <= -10:
                    status = "ربح 📈" if percent > 0 else "خسارة 📉"
                    msgs.append(f"{coin['symbol']}: {price} USDT\n{status}: {round(percent,2)}%")
        if msgs:
            bot.send_message(chat_id=int(user_id), text="\n\n".join(msgs))
        bot.send_message(chat_id=int(user_id), text="📰 الأخبار:\n" + "\n".join(fetch_news()))

@app.route("/")
def home():
    return "Crypto bot is running!"

def main():
    scheduler = BackgroundScheduler(timezone="Africa/Tunis")
    scheduler.add_job(daily_job, "cron", hour=20, minute=0)
    scheduler.start()

    app_telegram = ApplicationBuilder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_command))
    app_telegram.add_handler(CommandHandler("addcoin", addcoin))
    app_telegram.add_handler(CommandHandler("removecoin", removecoin))
    app_telegram.add_handler(CommandHandler("lang", lang))
    app_telegram.add_handler(CommandHandler("stats", stats))
    app_telegram.add_handler(CommandHandler("news", news))
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
