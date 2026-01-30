import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from tradingview_ta import TA_Handler, Interval
import nest_asyncio

nest_asyncio.apply()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT"
])

TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

USERS_FILE = "users.txt"

# ================= HELPERS =================
def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(str(u) for u in users))

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return [int(x.strip()) for x in f if x.strip().isdigit()]

async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def coins_keyboard(page=0, per_page=9):
    start = page * per_page
    end = start + per_page
    chunk = COINS[start:end]

    keyboard, row = [], []
    for i, coin in enumerate(chunk, 1):
        row.append(
            InlineKeyboardButton(
                coin.replace("USDT",""),
                callback_data=f"coin:{coin}"
            )
        )
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

# ================= SIGNAL LOGIC =================
def build_signal(price, rec, strength):
    if rec == "BUY":
        sl = price * 0.80
        tp1 = price * 1.50
        tp2 = price * 1.75
        tp3 = price * 2.00
    else:
        sl = price * 1.20
        tp1 = price * 0.50
        tp2 = price * 0.25
        tp3 = price * 0.00

    tps = []
    if strength >= 1:
        tps.append(("TP1", tp1))
    if strength >= 2:
        tps.append(("TP2", tp2))
    if strength >= 3:
        tps.append(("TP3", tp3))

    return sl, tps

def get_signal(symbol, exchange="BINANCE"):
    for tf_name, tf in TIMEFRAMES.items():
        try:
            handler = TA_Handler(
                symbol=symbol,
                screener="crypto",
                exchange=exchange,
                interval=tf
            )
            analysis = handler.get_analysis()
        except:
            continue

        rec = analysis.summary.get("RECOMMENDATION")
        if rec not in ["STRONG_BUY", "STRONG_SELL"]:
            continue

        osc = analysis.summary.get("OSCILLATORS", 0)
        ma = analysis.summary.get("MOVING_AVERAGES", 0)
        strength_score = abs(osc) + abs(ma)

        if strength_score >= 20:
            strength = 3
        elif strength_score >= 14:
            strength = 2
        elif strength_score >= 8:
            strength = 1
        else:
            return None

        price = float(analysis.indicators["close"])
        side = "BUY" if rec == "STRONG_BUY" else "SELL"

        sl, tps = build_signal(price, side, strength)

        return {
            "symbol": symbol,
            "tf": tf_name,
            "side": side,
            "entry": price,
            "sl": sl,
            "tps": tps,
            "exchange": exchange
        }
    return None

def get_multi_exchange_signal(symbol):
    sig = get_signal(symbol, "BINANCE")
    if sig:
        return sig
    return get_signal(symbol, "BYBIT")

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(
            f"Join {CHANNEL_USERNAME} first"
        )
        return

    await update.message.reply_text(
        "Select coin:",
        reply_markup=coins_keyboard()
    )

async def coin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    symbol = q.data.split(":")[1]
    sig = get_multi_exchange_signal(symbol)

    if not sig:
        await q.edit_message_text("⚠️ Signal ba STRONG ba.")
        return

    tp_text = "\n".join([f"🎯 {n}: {v:.4f}" for n, v in sig["tps"]])

    msg = f"""
📊 {sig['symbol']} ({sig['tf']}) {sig['exchange']}
📈 {sig['side']}
🎯 Entry: {sig['entry']:.4f}
🛑 SL: {sig['sl']:.4f}

{tp_text}
"""
    await q.edit_message_text(msg)

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_callback, pattern="coin:"))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
