import os
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from tradingview_ta import TA_Handler, Interval, Exchange

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")  # verified channel

ALLOWED_SIGNALS = [
    "STRONG_BUY",
    "BUY",
    "SELL",
    "STRONG_SELL"
]

SL = "-20%"
TP1 = "+50%"
TP2 = "+75%"
TP3 = "+100%"

COINS_FILE = "coins.txt"
INTERVAL = Interval.INTERVAL_1_HOUR

# ================= DATA =================
USERS = set()
AUTO_SIGNAL_RUNNING = False
COINS = []

# ================= LOAD COINS =================
def load_coins():
    global COINS
    if os.path.exists(COINS_FILE):
        with open(COINS_FILE, "r") as f:
            COINS = [c.strip().upper() for c in f if c.strip()]

# ================= TRADINGVIEW ANALYSIS =================
def analyze_coin(symbol: str):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange=Exchange.BINANCE,
        interval=INTERVAL
    )
    analysis = handler.get_analysis()
    return analysis.summary["RECOMMENDATION"], analysis.indicators["close"]

# ================= SIGNAL FORMAT =================
def format_signal(symbol, direction, price):
    return f"""
🚨 NEW SIGNAL
{symbol} (1H)
{direction} @ BINANCE

Entry: {price}

SL: {SL}
TP1: {TP1}
TP2: {TP2}
TP3: {TP3}
"""

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    USERS.add(update.effective_user.id)
    await update.message.reply_text("✅ Bot yana aiki.")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"👥 Users: {len(USERS)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = " ".join(context.args)
    for uid in USERS:
        try:
            await context.bot.send_message(uid, text)
        except:
            pass

# ================= COINS BUTTON =================
PAGE_SIZE = 10

def coins_keyboard(page=0):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    buttons = [
        [InlineKeyboardButton(c, callback_data=f"coin_{c}")]
        for c in COINS[start:end]
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"page_{page-1}"))
    if end < len(COINS):
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"page_{page+1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)

async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🪙 Coins whitelist:",
        reply_markup=coins_keyboard(0)
    )

async def coins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        await query.edit_message_reply_markup(
            reply_markup=coins_keyboard(page)
        )

    elif data.startswith("coin_"):
        symbol = data.replace("coin_", "")
        try:
            result, price = analyze_coin(symbol)
            if result not in ALLOWED_SIGNALS:
                await query.message.reply_text("⚠️ Signal ba STRONG ba ko NEUTRAL.")
                return

            direction = "BUY" if "BUY" in result else "SELL"
            msg = format_signal(symbol, direction, price)
            await query.message.reply_text(msg)

        except Exception as e:
            await query.message.reply_text("❌ Error yayin analysis.")

# ================= AUTO SIGNAL =================
async def auto_signal_loop(app):
    global AUTO_SIGNAL_RUNNING
    AUTO_SIGNAL_RUNNING = True

    while AUTO_SIGNAL_RUNNING:
        for symbol in COINS:
            try:
                result, price = analyze_coin(symbol)
                if result not in ALLOWED_SIGNALS:
                    continue

                direction = "BUY" if "BUY" in result else "SELL"
                msg = format_signal(symbol, direction, price)

                await app.bot.send_message(CHANNEL_ID, msg)
                await asyncio.sleep(5)

            except:
                continue

        await asyncio.sleep(60)

# ================= MAIN =================
async def main():
    load_coins()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("coins", coins))
    app.add_handler(CallbackQueryHandler(coins_callback))

    asyncio.create_task(auto_signal_loop(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
