import requests
import datetime
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

nest_asyncio.apply()  # حل مشكلة event loop موجود مسبقًا

TOKEN = "7963071210:AAGEHgS48YIbjHSCBehb6aYDM-vVvzKq7DE"
CRYPTO_API_KEY = "fd405453b43afbd4a8b7919d6dff0fe50fb0e584acc5cf858a1fa6e0c66f928a"
NEWS_API_KEY = "4e7fb52de4f44feca32a9110ecd1150f"

users_data = {}

LANGS = {
    "ar": {
        "welcome": "مرحبا بك! تم تفعيل التنبيه اليومي.",
        "stats_header": "📈 حالة العملات:",
        "no_coins": "لم تقم بإضافة عملات بعد.",
        "add_coin_prompt": "أرسل رمز العملة الذي تريد إضافته (مثلاً: BTC):",
        "add_coin_done": "تم إضافة العملة {} بنجاح.",
        "remove_coin_prompt": "أرسل رمز العملة الذي تريد حذفها:",
        "remove_coin_done": "تم حذف العملة {} بنجاح.",
        "help": (
            "/start - تفعيل البوت\n"
            "/stats - عرض حالة العملات\n"
            "/news - عرض أخبار العملات\n"
            "/addcoin - إضافة عملة\n"
            "/rmcoin - حذف عملة\n"
            "/lang - تغيير اللغة (ar أو en)\n"
            "/help - عرض الأوامر"
        ),
        "lang_changed": "تم تغيير اللغة إلى العربية.",
        "lang_invalid": "لغة غير مدعومة.",
        "profit_alert": "✅ تم تحقيق ربح 20% أو أكثر على {}!",
        "loss_alert": "⚠️ انخفض سعر {} بنسبة 10% أو أكثر!",
        "daily_report": "🕗 التقرير اليومي:\n",
        "invalid_symbol": "رمز عملة غير صالح، حاول مرة أخرى.",
        "enter_amount": "أرسل كمية العملة التي اشتريتها (مثلاً: 3.5):",
        "invalid_amount": "الكمية غير صالحة، حاول مرة أخرى.",
        "enter_buy_price": "أرسل سعر الشراء لكل وحدة (مثلاً: 18.5):",
        "invalid_price": "سعر غير صالح، حاول مرة أخرى.",
        "coin_not_found": "العملة غير موجودة في قائمتك.",
    },
    "en": {
        "welcome": "Welcome! Daily alerts activated.",
        "stats_header": "📈 Crypto Status:",
        "no_coins": "You have not added any coins yet.",
        "add_coin_prompt": "Send the coin symbol to add (e.g. BTC):",
        "add_coin_done": "Coin {} added successfully.",
        "remove_coin_prompt": "Send the coin symbol to remove:",
        "remove_coin_done": "Coin {} removed successfully.",
        "help": (
            "/start - Activate bot\n"
            "/stats - Show coin status\n"
            "/news - Show news\n"
            "/addcoin - Add a coin\n"
            "/rmcoin - Remove a coin\n"
            "/lang - Change language (ar or en)\n"
            "/help - Show commands"
        ),
        "lang_changed": "Language changed to English.",
        "lang_invalid": "Unsupported language.",
        "profit_alert": "✅ Profit of 20% or more achieved on {}!",
        "loss_alert": "⚠️ Price of {} dropped by 10% or more!",
        "daily_report": "🕗 Daily report:\n",
        "invalid_symbol": "Invalid coin symbol, try again.",
        "enter_amount": "Send the amount you bought (e.g. 3.5):",
        "invalid_amount": "Invalid amount, try again.",
        "enter_buy_price": "Send the buy price per unit (e.g. 18.5):",
        "invalid_price": "Invalid price, try again.",
        "coin_not_found": "Coin not found in your list.",
    },
}

ADDING_COIN, ADD_AMOUNT, ADD_PRICE, REMOVING_COIN = range(4)

def get_user_data(user_id):
    if user_id not in users_data:
        users_data[user_id] = {"coins": {}, "lang": "ar"}
    return users_data[user_id]

def get_prices(symbols):
    if not symbols:
        return {}
    syms = ",".join(symbols).upper()
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={syms}&tsyms=USD"
    headers = {"authorization": f"Apikey {CRYPTO_API_KEY}"}
    resp = requests.get(url, headers=headers)
    return resp.json()

def build_stats_message(user_data):
    coins = user_data["coins"]
    lang = LANGS[user_data["lang"]]
    if not coins:
        return lang["no_coins"]

    symbols = list(coins.keys())
    prices = get_prices(symbols)

    message = lang["stats_header"] + "\n"
    for sym, data in coins.items():
        if sym in prices:
            current = prices[sym]["USD"]
            buy_price = data["buy_price"]
            amount = data["amount"]
            diff = current - buy_price
            percent = (diff / buy_price) * 100
            profit = round(diff * amount, 2)
            emoji = "✅" if diff >= 0 else "❌"
            message += f"\n{emoji} {sym}: {current}$ | Buy: {buy_price}$ => {round(percent,2)}% ({profit}$)"
    return message

def get_news(symbols, lang_code):
    lang = "ar" if lang_code == "ar" else "en"
    query = " OR ".join(symbols) if symbols else "crypto"
    url = (
        f"https://newsapi.org/v2/everything?q={query}&language={lang}"
        f"&pageSize=3&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    )
    response = requests.get(url)
    articles = response.json().get("articles", [])
    news_msg = ""
    for a in articles:
        title = a.get("title", "")
        url = a.get("url", "")
        news_msg += f"\n- {title}\n{url}\n"
    return news_msg if news_msg else ("لا توجد أخبار حالياً" if lang_code == "ar" else "No news at the moment")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["welcome"])

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    msg = build_stats_message(user_data)
    await update.message.reply_text(msg)

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    coins = list(user_data["coins"].keys())
    lang_code = user_data["lang"]
    news_msg = get_news(coins, lang_code)
    await update.message.reply_text(news_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["help"])

async def addcoin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    await update.message.reply_text(LANGS[user_data["lang"]]["add_coin_prompt"])
    return ADDING_COIN

async def addcoin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    symbol = update.message.text.strip().upper()
    prices = get_prices([symbol])
    if symbol not in prices:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_symbol"])
        return ADDING_COIN

    context.user_data["add_coin_symbol"] = symbol
    await update.message.reply_text(LANGS[user_data["lang"]]["enter_amount"])
    return ADD_AMOUNT

async def addcoin_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    try:
        amount = float(update.message.text.strip())
        context.user_data["add_coin_amount"] = amount
    except:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_amount"])
        return ADD_AMOUNT

    await update.message.reply_text(LANGS[user_data["lang"]]["enter_buy_price"])
    return ADD_PRICE

async def addcoin_buy_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    try:
        buy_price = float(update.message.text.strip())
    except:
        await update.message.reply_text(LANGS[user_data["lang"]]["invalid_price"])
        return ADD_PRICE

    symbol = context.user_data.get("add_coin_symbol")
    amount = context.user_data.get("add_coin_amount")
    if symbol and amount:
        user_data["coins"][symbol] = {"amount": amount, "buy_price": buy_price}
        await update.message.reply_text(LANGS[user_data["lang"]]["add_coin_done"].format(symbol))
    else:
        await update.message.reply_text("Error, try again.")

    context.user_data.pop("add_coin_symbol", None)
    context.user_data.pop("add_coin_amount", None)

    return ConversationHandler.END

async def rmcoin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    if not user_data["coins"]:
        await update.message.reply_text(LANGS[user_data["lang"]]["no_coins"])
        return ConversationHandler.END
    await update.message.reply_text(LANGS[user_data["lang"]]["remove_coin_prompt"])
    return REMOVING_COIN

async def rmcoin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    symbol = update.message.text.strip().upper()
    if symbol in user_data["coins"]:
        user_data["coins"].pop(symbol)
        await update.message.reply_text(LANGS[user_data["lang"]]["remove_coin_done"].format(symbol))
    else:
        await update.message.reply_text(LANGS[user_data["lang"]]["coin_not_found"])
    return ConversationHandler.END

async def lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Send /lang ar or /lang en")
        return
    lang_code = args[0].lower()
    if lang_code not in LANGS:
        await update.message.reply_text(LANGS[user_data["lang"]]["lang_invalid"])
        return
    user_data["lang"] = lang_code
    await update.message.reply_text(LANGS[lang_code]["lang_changed"])

async def check_price_alerts(app):
    while True:
        for user_id, data in users_data.items():
            coins = data["coins"]
            lang_code = data["lang"]
            prices = get_prices(list(coins.keys()))
            for sym, cdata in coins.items():
                if sym in prices:
                    current = prices[sym]["USD"]
                    buy_price = cdata["buy_price"]
                    diff = current - buy_price
                    percent = (diff / buy_price) * 100
                    if percent >= 20:
                        await app.bot.send_message(user_id, LANGS[lang_code]["profit_alert"].format(sym))
                    elif percent <= -10:
                        await app.bot.send_message(user_id, LANGS[lang_code]["loss_alert"].format(sym))
        await asyncio.sleep(300)  # كل 5 دقائق

async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.chat_id
    data = users_data.get(user_id)
    if not data:
        return
    lang_code = data["lang"]
    stats_msg = build_stats_message(data)
    news_msg = get_news(list(data["coins"].keys()), lang_code)
    msg = LANGS[lang_code]["daily_report"] + stats_msg + "\n\n" + news_msg
    await context.bot.send_message(chat_id=user_id, text=msg)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lang", lang))

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("addcoin", addcoin_start)],
        states={
            ADDING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_receive)],
            ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_amount)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addcoin_buy_price)],
        },
        fallbacks=[],
    )
    app.add_handler(add_conv)

    rm_conv = ConversationHandler(
        entry_points=[CommandHandler("rmcoin", rmcoin_start)],
        states={REMOVING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rmcoin_receive)]},
        fallbacks=[],
    )
    app.add_handler(rm_conv)

    # جدول التقرير اليومي الساعة 20:00 توقيت تونس (UTC+1)
    tz_offset = 1
    hour_utc = (20 - tz_offset) % 24
    app.job_queue.run_daily(daily_report, time=datetime.time(hour=hour_utc, minute=0, second=0))

    # بدء مهمة التنبيهات الفورية
    asyncio.create_task(check_price_alerts(app))

    print("⚡ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
