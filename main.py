import os
import json
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# 🔹 Environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# 📦 Data read/write
def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 💰 Handle messages (+income, -expense)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    text = update.message.text.strip()
    if not text:
        return
    data = load_data()
    today = str(datetime.date.today())
    if today not in data:
        data[today] = []

    if text.startswith("+"):
        try:
            parts = text[1:].strip().split(" ", 1)
            amount = int(parts[0])
            desc = parts[1] if len(parts) > 1 else "daromad"
            data[today].append({"type": "income", "amount": amount, "desc": desc})
            await update.message.reply_text(f"✅ {amount} so‘m daromad qo‘shildi ({desc})")
        except:
            await update.message.reply_text("❗ Format: +summa izoh")
    elif text.startswith("-"):
        try:
            parts = text[1:].strip().split(" ", 1)
            amount = int(parts[0])
            desc = parts[1] if len(parts) > 1 else "xarajat"
            data[today].append({"type": "expense", "amount": amount, "desc": desc})
            await update.message.reply_text(f"💸 {amount} so‘m xarajat qo‘shildi ({desc})")
        except:
            await update.message.reply_text("❗ Format: -summa izoh")
    else:
        await update.message.reply_text("💡 Misol: +4500000 oylik yoki -25000 bozor")
        return

    save_data(data)

# 📊 Hisobot menu
async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 Bugungi", callback_data="hisobot_bugun")],
        [InlineKeyboardButton("🗓 Oylik", callback_data="hisobot_oy")],
        [InlineKeyboardButton("📘 Yillik", callback_data="hisobot_yil")],
    ]
    await update.message.reply_text("Hisobot turini tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

# 🔍 Calculate report
def hisobla(data, start_date=None, end_date=None):
    income, expense = 0, 0
    details = {}
    for date_str, records in data.items():
        d = datetime.date.fromisoformat(date_str)
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        for r in records:
            if r["type"] == "income":
                income += r["amount"]
            else:
                expense += r["amount"]
                details[r["desc"]] = details.get(r["desc"], 0) + r["amount"]
    balance = income - expense
    return income, expense, balance, details

# 📘 Format yearly report
def format_yillik(data, year):
    total_income = total_expense = 0
    text = f"📘 MeningSoqqam — {year}-yil hisobot 🧾\n\n"
    for month in range(1, 13):
        start = datetime.date(year, month, 1)
        end_day = datetime.date(year, month % 12 + 1, 1) - datetime.timedelta(days=1) if month < 12 else datetime.date(year, 12, 31)
        inc, exp, bal, _ = hisobla(data, start, end_day)
        if inc == exp == 0:
            continue
        total_income += inc
        total_expense += exp
        text += f"🗓 {start.strftime('%B')}\nDaromad: {inc:,}\nXarajat: {exp:,}\nBalans: {bal:,}\n────────────────────\n"
    total_balance = total_income - total_expense
    text += f"\n📘 Umumiy {year}-yil natijasi:\n💵 Daromad: {total_income:,}\n💸 Xarajat: {total_expense:,}\n💰 Sof balans: {total_balance:,}\n"
    return text

# 📆 Callback query
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    today = datetime.date.today()

    if query.data == "hisobot_bugun":
        start = end = today
        title = f"📅 Bugungi hisobot ({today})"
    elif query.data == "hisobot_oy":
        start = today.replace(day=1)
        end = today
        title = f"🗓 Oylik hisobot ({today.strftime('%B %Y')})"
    else:
        year = today.year
        text = format_yillik(data, year)
        await query.edit_message_text(text)
        return

    income, expense, balance, details = hisobla(data, start, end)
    msg = f"{title}\n\n💵 Daromad: {income:,}\n💸 Xarajat: {expense:,}\n💰 Balans: {balance:,}\n"
    if details:
        msg += "\nEng ko‘p xarajatlar:\n"
        top = sorted(details.items(), key=lambda x: x[1], reverse=True)[:5]
        for name, val in top:
            msg += f"- {name}: {val:,}\n"
    await query.edit_message_text(msg)

# 🕒 Scheduled reports
async def kunlik_hisobot(app):
    data = load_data()
    today = datetime.date.today()
    inc, exp, bal, _ = hisobla(data, today, today)
    msg = f"📅 Bugungi hisobot ({today})\n💵 Daromad: {inc:,}\n💸 Xarajat: {exp:,}\n💰 Balans: {bal:,}"
    await app.bot.send_message(chat_id=CHAT_ID, text=msg)

async def oylik_hisobot(app):
    data = load_data()
    today = datetime.date.today()
    start = today.replace(day=1)
    inc, exp, bal, _ = hisobla(data, start, today)
    msg = f"🗓 Oylik hisobot ({today.strftime('%B %Y')})\n💵 Daromad: {inc:,}\n💸 Xarajat: {exp:,}\n💰 Balans: {bal:,}"
    await app.bot.send_message(chat_id=CHAT_ID, text=msg)

# 🚀 Main function
async def main():
    print("✅ MeningSoqqam ishga tushdi...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("hisobot", hisobot))
    app.add_handler(CallbackQueryHandler(callback))

    # Scheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(lambda: asyncio.create_task(kunlik_hisobot(app)), "cron", hour=22, minute=0)
    scheduler.add_job(lambda: asyncio.create_task(oylik_hisobot(app)), "cron", day=1, hour=0, minute=0)
    scheduler.start()

    await app.run_polling(stop_signals=None)

# 🔹 Run without asyncio.run() conflict
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.get_event_loop().create_task(main())
