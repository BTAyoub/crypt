import os
import requests
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from flask import Flask
from threading import Thread

# توكن بوت تيليجرام
TOKEN = "8028036634:AAFS_FjnPrzLw1B-qYp2l1VCoYJBcRcXiv8"

# مفاتيح API
CRYPTO_API_KEY = "fd405453b43afbd4a8b7919d6dff0fe50fb0e584acc5cf858a1fa6e0c66f928a"
NEWS_API_KEY = "4e7fb52de4f44feca32a9110ecd1150f"

# Flask app
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "بوت العملات الرقمية يعمل بنجاح!"

# أوضاع المحادثة
ADD_COIN, ADD_AMOUNT, ADD_PRICE, REMOVE_COIN = range(4)

# بيانات المستخدمين (بالذاكرة فقط)
users_data = {}

LANGS = {
    "ar": {
        "welcome": "مرحبًا! تم تفعيل البوت والتنبيهات اليومية.",
        "stats_header": "📊 حالة العملات:",
        "no_coins": "لم تقم بإضافة أي عملات حتى الآن.",
        "add_coin_prompt": "أرسل رمز العملة لإضافتها (مثل BTC):",
        "add_amount_prompt": "أرسل كمية العملة التي اشتريتها:",
        "add_price_prompt": "أرسل سعر الشراء لكل وحدة:",
        "add_done": "تمت إضافة العملة بنجاح.",
        "remove_coin_prompt": "أرسل رمز العملة التي تريد حذفها:",
        "remove_done": "تم حذف العملة بنجاح.",
        "help_text": (
            "/start - بدء البوت\n"
            "/stats - عرض حالة العملات\n"
            "/news - عرض الأخبار\n"
            "/addcoin - إضافة عملة\n"
            "/rmcoin - حذف عملة\n"
            "/lang - تغيير اللغة (ar أو en)\n"
            "/help - عرض الأوامر"
        ),
        "lang_changed": "تم تغيير اللغة إلى العربية.",
        "lang_invalid": "لغة غير مدعومة.",
        "invalid_symbol": "رمز عملة غير صالح. حاول مرة أخرى.",
        "invalid_number": "القيمة غير صالحة. حاول مرة أخرى.",
        "coin_not_found": "العملة غير موجودة في قائمتك.",
        "profit_alert": "✅ عملة {} حققت ربح 20٪ أو أكثر!",
        "loss_alert": "⚠️ عملة {} انخفض سعرها بنسبة 10٪ أو أكثر!",
        "daily_report": "🕗 التقرير اليومي:\n",
    },
    "en": {
        "welcome": "Welcome! Bot and daily alerts activated.",
        "stats_header": "📊 Crypto Status:",
        "no_coins": "You have not added any coins yet.",
        "add_coin_prompt": "Send the coin symbol to add (e.g. BTC):",
        "add_amount_prompt": "Send the amount you bought:",
        "add_price_prompt": "Send the buy price per unit:",
        "add_done": "Coin added successfully.",
        "remove_coin_prompt": "Send the coin symbol to remove:",
        "remove_done": "Coin removed successfully.",
        "help_text": (
            "/start - Start bot\n"
            "/stats - Show coin status\n"
            "/news - Show news\n"
            "/addcoin - Add coin\n"
            "/rmcoin - Remove coin\n"
            "/lang - Change language (ar or en)\n"
            "/help - Show commands"
        ),
        "lang_changed": "Language changed to English.",
        "lang_invalid": "Unsupported language.",
        "invalid_symbol": "Invalid coin symbol. Try again.",
        "invalid_number": "Invalid value. Try again.",
        "coin_not_found": "Coin not found in your list.",
        "profit_alert": "✅ Coin {} made 20%+ profit!",
        "loss_alert": "⚠️ Coin {} price dropped by 10%+!",
        "daily_report": "🕗 Daily report:\n",
    },
}

def get_user_data(user_id):
    if user_id not in users_data:
        users_data[user_id] = {"coins": {}, "lang": "ar"}
    return users_data[user_id]

def fetch_prices(symbols):
    if not symbols:
        return {}
    symbols_str = ",".join(symbols).upper()
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={symbols_str}&tsyms=USD"
    headers = {"authorization": f"Apikey {CRYPTO_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        return data
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return {}

def build_stats(user_data):
    coins = user_data["coins"]
    lang = LANGS[user_data["lang"]]
    if not coins:
        return lang["no_coins"]
    prices = fetch_prices(list(coins.keys()))
    msg = lang["stats_header"] + "\n"
    for sym, info in coins.items():
        if sym in prices and "USD" in prices[sym]:
            current_price = prices[sym]["USD"]
            buy_price = info["buy_price"]
            amount = info["amount"]
            change_percent = ((current_price - buy_price) / buy_price) * 100
            total_profit = (current_price - buy_price) * amount
            emoji = "✅" if change_percent >= 0 else "❌"
            msg += f"\n{emoji} {sym}: ${current_price:.2f} | Buy: ${buy_price:.2f} | Change: {change_percent:.2f}% | Profit: ${total_profit:.2f}"
    return msg

def fetch_news(symbols, lang_code):
    lang = "ar" if lang_code == "ar" else "en"
    query = " OR ".join(symbols) if symbols else "crypto"
    url = f"https://newsapi.org/v2/everything?q={query}&language={lang}&pageSize=3&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        articles = resp.json().get("articles", [])
        if not articles:
            return LANGS[lang_code]["no_coins"]
        news_text = ""
        for art in articles:
            title = art.get("title", "")
            url = art.get("url", "")
            news_text += f"\n- {title}\n{url}\n"
        return news_text
    except Exception as e:
        print(f"Error fetching news: {e}")
        return LANGS[lang_code]["no_coins"]

# أوامر البوت

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["welcome"])

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    msg = build_stats(user_data)
    await update.message.reply_text(msg)

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    coins = list(user_data["coins"].keys())
    news_text = fetch_news(coins, user_data["lang"])
    await update.message.reply_text(news_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["help_text"])

# إضافة عملة
async def addcoin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["add_coin_prompt"])
    return ADD_COIN

async def addcoin_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    symbol = update.message.text.upper()
    prices = fetch_prices([symbol])
    if symbol not in prices:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_symbol"])
        return ADD_COIN
    context.user_data["add_symbol"] = symbol
    await update.message.reply_text(LANGS[user_data["lang"]]["add_amount_prompt"])
    return ADD_AMOUNT

async def addcoin_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    try:
        amount = float(update.message.text)
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_number"])
        return ADD_AMOUNT
    context.user_data["add_amount"] = amount
    await update.message.reply_text(LANGS[user_data["lang"]]["add_price_prompt"])
    return ADD_PRICE

async def addcoin_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    try:
        price = float(update.message.text)
        if price <= 0:
            raise ValueError
    except:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_number"])
        return ADD_PRICE
    symbol = context.user_data["add_symbol"]
    amount = context.user_data["add_amount"]
    user_data["coins"][symbol] = {"amount": amount, "buy_price": price}
    await update.message.reply_text(LANGS[user_data["lang"]]["add_done"])
    return ConversationHandler.END

async def rmcoin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    if not user_data["coins"]:
        await update.message.reply_text(LANGS[user_data["lang"]]["no_coins"])
        return ConversationHandler.END
    await update.message.reply_text(LANGS[user_data["lang"]]["remove_coin_prompt"])
    return REMOVE_COIN

async def rmcoin_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    symbol = update.message.text.upper()
    if symbol not in user_data["coins"]:
        await update.message.reply_text(LANGS[user_data["lang"]]["coin_not_found"])
        return REMOVE_COIN
    del user_data["coins"][symbol]
    await update.message.reply_text(LANGS[user_data["lang"]]["remove_done"])
    return ConversationHandler.END

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /lang ar OR /lang en")
        return
    lang = args[0].lower()
    if lang not in LANGS:
        await update.message.reply_text(LANGS[user_data["lang"]]["lang_invalid"])
        return
    user_data["lang"] = lang
    await update.message.reply_text(LANGS[lang]["lang_changed"])

# مهمة إرسال التنبيهات اليومية
async def daily_alerts(app):
    while True:
        now = datetime.now()
        target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)  # 20:00 بتوقيت السيرفر
        if now > target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        for user_id, user_data in users_data.items():
            coins = user_data["coins"]
            lang = LANGS[user_data["lang"]]
            if not coins:
                continue
            prices = fetch_prices(list(coins.keys()))
            report = lang["daily_report"]
            for sym, info in coins.items():
                if sym not in prices or "USD" not in prices[sym]:
                    continue
                current_price = prices[sym]["USD"]
                buy_price = info["buy_price"]
                change_percent = ((current_price - buy_price) / buy_price) * 100

                if change_percent >= 20:
                    report += f"\n" + lang["profit_alert"].format(sym)
                elif change_percent <= -10:
                    report += f"\n" + lang["loss_alert"].format(sym)

            try:
                await app.bot.send_message(chat_id=user_id, text=report)
            except Exception:
                pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    addcoin_conv = ConversationHandler(
        entry_points=[CommandHandler("addcoin", addcoin_start)],
        states={
            ADD_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_symbol)],
            ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_amount)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    rmcoin_conv = ConversationHandler(
        entry_points=[CommandHandler("rmcoin", rmcoin_start)],
        states={
            REMOVE_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rmcoin_symbol)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(addcoin_conv)
    app.add_handler(rmcoin_conv)

    # تشغيل مهمة التنبيه اليومي بالخلفية
    loop = asyncio.get_event_loop()
    loop.create_task(daily_alerts(app))

    # تشغيل Flask في ثريد منفصل (لتفادي حظر الحدث الرئيسي)
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: flask_app.run(host="0.0.0.0", port=port)).start()

    print("Bot started...")
    app.run_polling()
