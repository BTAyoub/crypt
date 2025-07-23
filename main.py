
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import datetime
from keep_alive import keep_alive
keep_alive()

TOKEN = "7963071210:AAGEHgS48YIbjHSCBehb6aYDM-vVvzKq7DE"
CHAT_ID = None

WATCHED_COINS = {
    "solana": {"symbol": "SOL", "buy_price": 198, "amount": 6},
    "chainlink": {"symbol": "LINK", "buy_price": 18.92, "amount": 5},
    "ripple": {"symbol": "XRP", "buy_price": 3.43, "amount": 5},
}

def get_prices():
    ids = ",".join(WATCHED_COINS.keys())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    response = requests.get(url)
    return response.json()

def build_status():
    prices = get_prices()
    message = "📈 حالة العملات:\n"
    for coin_id, data in WATCHED_COINS.items():
        if coin_id in prices:
            current = prices[coin_id]['usd']
            diff = current - data['buy_price']
            percent = (diff / data['buy_price']) * 100
            profit = round(diff * data['amount'], 2)
            emoji = "✅" if diff >= 0 else "❌"
            message += f"\n{emoji} {data['symbol']}: {current}$ | اشترينا بـ {data['buy_price']}$ => {round(percent, 2)}% ({profit}$)"
    return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id
    await update.message.reply_text("مرحبا بك! تم تفعيل التنبيه اليومي.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_status())

async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    if CHAT_ID:
        await context.bot.send_message(chat_id=CHAT_ID, text=build_status())

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    app.job_queue.run_daily(daily_report, time=datetime.time(hour=9, minute=0, second=0))

    print("⚡ Bot is running...")
    app.run_polling()
