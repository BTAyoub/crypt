import logging
import requests
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

TOKEN = "8028036634:AAFS_FjnPrzLw1B-qYp2l1VCoYJBcRcXiv8"
CHAT_ID = None  # سيتم تحديثها عند أول استخدام

# بيانات العملات
COINS = {
    "solana": {"symbol": "SOL", "amount": 6, "buy_price": 198},
    "chainlink": {"symbol": "LINK", "amount": 5, "buy_price": 18.92},
    "ripple": {"symbol": "XRP", "amount": 5, "buy_price": 3.43}
}

HEADERS = {"accept": "application/json"}

def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        r = requests.get(url, headers=HEADERS)
        return r.json()[coin_id]["usd"]
    except:
        return None

async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = "📊 تحديث يومي لحالة العملات:\n\n"
    for coin_id, data in COINS.items():
        current_price = get_price(coin_id)
        if current_price:
            amount = data["amount"]
            total_buy = amount * data["buy_price"]
            current_value = amount * current_price
            diff = current_value - total_buy
            status = "🟢 ربح" if diff > 0 else "🔴 خسارة"
            report += f"• {data['symbol']}:\n"
            report += f"  السعر الآن: {current_price}$\n"
            report += f"  {status}: {round(diff, 2)}$\n\n"
    await context.bot.send_message(chat_id=CHAT_ID, text=report)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    await update.message.reply_text("✅ تم تفعيل التنبيهات الخاصة بك.\nسيتم إرسال التحديثات اليومية تلقائيًا.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # جدولة إشعار كل 24 ساعة (يمكن تغيير الوقت)
    app.job_queue.run_repeating(daily_report, interval=86400, first=10)

    print("Bot started...")
    app.run_polling()
