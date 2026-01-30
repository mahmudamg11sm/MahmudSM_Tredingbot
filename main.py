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
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

# 100+ coins (example major + alts)
COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT",
    "MATICUSDT","DOTUSDT","LINKUSDT","LTCUSDT","TRXUSDT","ATOMUSDT","ETCUSDT",
    "FILUSDT","NEARUSDT","APTUSDT","OPUSDT","ARBUSDT","SUIUSDT","INJUSDT",
    "RNDRUSDT","IMXUSDT","STXUSDT","ICPUSDT","AAVEUSDT","UNIUSDT","XLMUSDT",
    "EOSUSDT","XTZUSDT","THETAUSDT","MKRUSDT","SNXUSDT","KAVAUSDT","FLOWUSDT",
    "GALAUSDT","APEUSDT","CHZUSDT","CRVUSDT","SANDUSDT","MANAUSDT","DYDXUSDT",
    "RUNEUSDT","KSMUSDT","ZILUSDT","ENJUSDT","WAVESUSDT","ONEUSDT","CELOUSDT",
    "MINAUSDT","QTUMUSDT","NEOUSDT","HBARUSDT","IOTAUSDT","ROSEUSDT","CFXUSDT",
    "LDOUSDT","PEPEUSDT","FLOKIUSDT","BONKUSDT","JUPUSDT","WIFUSDT","TIAUSDT",
    "SEIUSDT","BLURUSDT","PYTHUSDT","ORDIUSDT","MEMEUSDT","AXSUSDT","ILVUSDT",
    "GMXUSDT","COMPUSDT","YFIUSDT","MASKUSDT","ANKRUSDT","SKLUSDT","COTIUSDT"
])

PAGE_SIZE = 10

TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS
}

# ================= HELPERS =================
async def is_user_in_channel(context, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# ================= SIGNAL LOGIC =================
def build_signal(rec, price):
    if rec == "STRONG_BUY":
        return {
            "rec": "BUY",
            "sl": price * 0.80,     # -20%
            "tp1": price * 1.50,   # +50%
            "tp2": price * 1.75,   # +75%
            "tp3": price * 2.00    # +100%
        }
    else:
        return None

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
            rec = analysis.summary.get("RECOMMENDATION")

            if rec == "STRONG_BUY":
                price = float(analysis.indicators["close"])
                sig = build_signal(rec, price)
                sig.update({
                    "symbol": symbol,
                    "tf": tf_name,
                    "exchange": exchange,
                    "entry": price
                })
                return sig
        except:
            continue
    return None

def get_multi_exchange_signal(symbol):
    for ex in ("BINANCE", "BYBIT"):
        sig = get_signal(symbol, ex)
        if sig:
            return sig
    return None

# ================= UI =================
def coins_keyboard(page=0):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    buttons = [
        [InlineKeyboardButton(c, callback_data=f"coin:{c}")]
        for c in COINS[start:end]
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"page:{page-1}"))
    if end < len(COINS):
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"page:{page+1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(buttons)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")]
        ])
        await update.message.reply_text("Da fari ka shiga channel:", reply_markup=btn)
        return

    await update.message.reply_text(
        "📊 Zaɓi coin ko rubuta sunansa:",
        reply_markup=coins_keyboard(0)
    )

async def coins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    if data.startswith("page:"):
        page = int(data.split(":")[1])
        await q.edit_message_reply_markup(reply_markup=coins_keyboard(page))

    elif data.startswith("coin:"):
        coin = data.split(":")[1]
        await send_signal(q.message, coin)

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"

    await send_signal(update.message, text)

async def send_signal(message, symbol):
    sig = get_multi_exchange_signal(symbol)

    if not sig:
        await message.reply_text("⚠️ Signal ba STRONG ba ko babu.")
        return

    msg = (
        f"📊 SIGNAL {sig['symbol']} ({sig['tf']})\n"
        f"📈 BUY @ {sig['exchange']}\n\n"
        f"🎯 Entry: {sig['entry']:.4f}\n"
        f"🛑 SL: {sig['sl']:.4f}\n"
        f"💰 TP1: {sig['tp1']:.4f}\n"
        f"💰 TP2: {sig['tp2']:.4f}\n"
        f"💰 TP3: {sig['tp3']:.4f}"
    )

    await message.reply_text(msg)

# ================= AUTO POST =================
async def auto_post(app):
    sent = set()
    while True:
        for coin in COINS:
            sig = get_multi_exchange_signal(coin)
            if not sig:
                continue

            key = f"{coin}-{sig['tf']}"
            if key in sent:
                continue

            msg = (
                f"🚨 NEW SIGNAL\n"
                f"{sig['symbol']} ({sig['tf']})\n"
                f"BUY @ {sig['exchange']}\n"
                f"Entry: {sig['entry']:.4f}"
            )

            try:
                await app.bot.send_message(CHANNEL_USERNAME, msg)
                sent.add(key)
            except:
                pass

        await asyncio.sleep(300)  # minti 5

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coins_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    app.create_task(auto_post(app))
    app.run_polling()

if __name__ == "__main__":
    main()
