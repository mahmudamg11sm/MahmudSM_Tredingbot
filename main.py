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
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return [int(x) for x in f.read().splitlines() if x.isdigit()]

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(map(str, users)))

async def is_user_in_channel(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= SIGNAL LOGIC =================
def build_signal(rec, price):
    if rec == "STRONG_BUY":
        return {
            "rec": "BUY",
            "entry": price,
            "sl": price * 0.80,      # -20%
            "tp1": price * 1.50,     # +50%
            "tp2": price * 1.75,     # +75%
            "tp3": price * 2.00      # +100%
        }
    else:
        return {
            "rec": "SELL",
            "entry": price,
            "sl": price * 1.20,
            "tp1": price * 0.50,
            "tp2": price * 0.25,
            "tp3": price * 0.00
        }

def get_signal(symbol, exchange):
    for tf_name, tf in TIMEFRAMES.items():
        try:
            handler = TA_Handler(
                symbol=symbol,
                screener="crypto",
                exchange=exchange,
                interval=tf
            )
            analysis = handler.get_analysis()
            rec = analysis.summary["RECOMMENDATION"]

            if rec in ["STRONG_BUY", "STRONG_SELL"]:
                price = float(analysis.indicators["close"])
                sig = build_signal(rec, price)
                sig.update({
                    "symbol": symbol,
                    "tf": tf_name,
                    "exchange": exchange
                })
                return sig
        except:
            continue
    return None

def get_multi_exchange_signal(symbol):
    for ex in ["BINANCE", "BYBIT"]:
        sig = get_signal(symbol, ex)
        if sig:
            return sig
    return None

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")]
        ])
        await update.message.reply_text("Da fari ka shiga channel:", reply_markup=btn)
        return

    await update.message.reply_text("Rubuta coin (BTC ko ETHUSDT):")

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper().strip()

    if len(text) < 3:
        return

    if not text.endswith("USDT"):
        text += "USDT"

    sig = get_multi_exchange_signal(text)

    if not sig:
        await update.message.reply_text("⚠️ Signal ba STRONG ba ko babu.")
        return

    msg = (
        f"📊 SIGNAL {sig['symbol']} ({sig['tf']})\n"
        f"📈 {sig['rec']} @ {sig['exchange']}\n\n"
        f"🎯 Entry: {sig['entry']:.4f}\n"
        f"🛑 SL: {sig['sl']:.4f}\n"
        f"💰 TP1: {sig['tp1']:.4f}\n"
        f"💰 TP2: {sig['tp2']:.4f}\n"
        f"💰 TP3: {sig['tp3']:.4f}"
    )

    await update.message.reply_text(msg)

# ================= AUTO POST (NO TIME LIMIT) =================
async def auto_post(app):
    sent = set()
    while True:
        for coin in COINS:
            sig = get_multi_exchange_signal(coin)
            if not sig:
                continue

            key = f"{coin}-{sig['tf']}-{sig['rec']}"
            if key in sent:
                continue

            msg = (
                f"🚨 NEW SIGNAL\n"
                f"{sig['symbol']} ({sig['tf']})\n"
                f"{sig['rec']} @ {sig['exchange']}\n"
                f"Entry: {sig['entry']:.4f}"
            )

            try:
                await app.bot.send_message(CHANNEL_USERNAME, msg)
                sent.add(key)
            except:
                pass

        await asyncio.sleep(300)  # duk minti 5

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    asyncio.create_task(auto_post(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
