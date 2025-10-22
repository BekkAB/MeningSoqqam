import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DB_FILE = "finance.db"

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            amount REAL,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_transaction(t_type, amount, note):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (date, type, amount, note) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d"), t_type, amount, note))
    conn.commit()
    conn.close()

def get_summary(days=1):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    cur.execute("SELECT type, SUM(amount) FROM transactions WHERE date >= ? GROUP BY type", (start_date,))
    data = cur.fetchall()
    conn.close()
    return data

# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 Salom! Men sizning kirim-chiqim hisob botingizman.\n\n"
        "Buyruqlar:\n"
        "/kirim 100000 ish haqi\n"
        "/chiqim 50000 non\n"
        "/bugun — bugungi hisobot\n"
        "/balans — umumiy balans"
    )

async def kirim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Masalan: /kirim 100000 ish haqi")
        return
    amount = float(context.args[0])
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    add_transaction("kirim", amount, note)
    await update.message.reply_text(f"✅ {amount:.0f} so‘m kirim qo‘shildi. {note}")

async def chiqim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Masalan: /chiqim 50000 choy")
        return
    amount = float(context.args[0])
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    add_transaction("chiqim", amount, note)
    await update.message.reply_text(f"💸 {amount:.0f} so‘m chiqim yozildi. {note}")

async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_summary(days=1)
    kirim_sum = sum(a for t, a in data if t == "kirim")
    chiqim_sum = sum(a for t, a in data if t == "chiqim")
    balance = kirim_sum - chiqim_sum
    await update.message.reply_text(
        f"📅 Bugungi hisobot:\n"
        f"Kirim: {kirim_sum:.0f} so‘m\n"
        f"Chiqim: {chiqim_sum:.0f} so‘m\n"
        f"Balans: {balance:.0f} so‘m"
    )

async def balans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
    data = cur.fetchall()
    conn.close()
    kirim_sum = sum(a for t, a in data if t == "kirim")
    chiqim_sum = sum(a for t, a in data if t == "chiqim")
    balance = kirim_sum - chiqim_sum
    await update.message.reply_text(
        f"💰 Umumiy balans:\n"
        f"Kirim: {kirim_sum:.0f}\n"
        f"Chiqim: {chiqim_sum:.0f}\n"
        f"Balans: {balance:.0f}"
    )

# === MAIN ===
async def main():
    init_db()
    TOKEN = os.getenv("TG_BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("TG_BOT_TOKEN o‘rnatilmagan.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kirim", kirim))
    app.add_handler(CommandHandler("chiqim", chiqim))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CommandHandler("balans", balans))

    print("✅ MeningSoqqam ishga tushdi...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
