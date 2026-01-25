import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")  # Example: @Mahmudsm1

TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

# ================= COINS =================
COINS = sorted(list(set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT"
])))

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def coins_keyboard(page=0, per_page=15):
    start = page * per_page
    end = start + per_page
    chunk = COINS[start:end]

    keyboard = []
    row = []

    for i, coin in enumerate(chunk, 1):
        row.append(InlineKeyboardButton(coin.replace("USDT",""), callback_data=f"coin:{coin}"))
        if i % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if end < len(COINS):
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))
    if nav:
        keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

# ================= SIGNAL =================
def get_signal(symbol: str):
    results = {}
    strong_signal = None

    for tf_name, tf_value in TIMEFRAMES.items():
        handler = TA_Handler(
            symbol=symbol,
            screener="crypto",
            exchange="BYBIT",
            interval=tf_value
        )
        analysis = handler.get_analysis()
        rec = analysis.summary["RECOMMENDATION"]
        results[tf_name] = rec

        # Track STRONG signals only
        if rec in ["STRONG_BUY", "STRONG_SELL"]:
            strong_signal = rec

    # Use last close price
    price = float(handler.get_analysis().indicators["close"])

    if strong_signal == "STRONG_BUY":
        entry = price
        sl = price * 0.97
        tp1 = price * 1.05
        tp2 = price * 1.12
        tp3 = price * 1.30
        rec = "STRONG BUY"
    elif strong_signal == "STRONG_SELL":
        entry = price
        sl = price * 1.03
        tp1 = price * 0.95
        tp2 = price * 0.88
        tp3 = price * 0.70
        rec = "STRONG SELL"
    else:
        entry = price
        sl = price * 0.99
        tp1 = price * 1.01
        tp2 = price * 1.02
        tp3 = price * 1.03
        rec = "NEUTRAL"

    return {
        "symbol": symbol,
        "rec": rec,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "tf": results
    }

# ================= AUTO POST =================
async def auto_scan_and_post(app):
    for coin in COINS:
        try:
            s = get_signal(coin)
            if s["rec"] in ["STRONG BUY", "STRONG SELL"]:
                msg = f"""
📊 Auto 4H Signal for {s['symbol']}

📈 Recommendation: {s['rec']}
🎯 Entry: {s['entry']:.4f}
🛑 SL: {s['sl']:.4f}
💰 TP1: {s['tp1']:.4f} | TP2: {s['tp2']:.4f} | TP3: {s['tp3']:.4f}

⏱ Timeframes: 1H={s['tf']['1H']}, 4H={s['tf']['4H']}, 1D={s['tf']['1D']}
⚠️ Not financial advice.
"""
                await app.bot.send_message(CHANNEL_USERNAME, msg)
        except Exception as e:
            logging.warning(f"Failed auto scan {coin}: {e}")

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Na shiga", callback_data="check_join")]
        ])
        await update.message.reply_text(f"Don amfani da bot, sai ka shiga channel:\n{CHANNEL_USERNAME}", reply_markup=btn)
        return
    await update.message.reply_text("Barka da zuwa Dynamic Auto Signal Bot 🚀\nZaɓi coin ko rubuta sunansa:", reply_markup=coins_keyboard(0))

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_in_channel(context, query.from_user.id):
        await query.edit_message_text("✅ An tabbatar! Zaɓi coin:", reply_markup=coins_keyboard(0))
    else:
        await query.answer("❌ Har yanzu baka shiga channel ba!", show_alert=True)

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("page:"):
        page = int(data.split(":")[1])
        await query.edit_message_reply_markup(reply_markup=coins_keyboard(page))
        return
    if data.startswith("coin:"):
        symbol = data.split(":")[1]
        try:
            s = get_signal(symbol)
            text = f"""
📊 Signal for {s['symbol']}

📈 Recommendation: {s['rec']}
🎯 Entry: {s['entry']:.4f}
🛑 SL: {s['sl']:.4f}
💰 TP1: {s['tp1']:.4f} | TP2: {s['tp2']:.4f} | TP3: {s['tp3']:.4f}
⏱ Timeframes: 1H={s['tf']['1H']}, 4H={s['tf']['4H']}, 1D={s['tf']['1D']}
⚠️ Not financial advice.
"""
            await query.edit_message_text(text)
        except:
            await query.edit_message_text("❌ An samu matsala wajen ɗauko signal.")

async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Da fari sai ka shiga {CHANNEL_USERNAME}")
        return
    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"
    try:
        s = get_signal(text)
        # Auto add to whitelist
        if text not in COINS:
            COINS.append(text)
            COINS.sort()
        msg = f"""
📊 Signal for {s['symbol']}

📈 Recommendation: {s['rec']}
🎯 Entry: {s['entry']:.4f}
🛑 SL: {s['sl']:.4f}
💰 TP1: {s['tp1']:.4f} | TP2: {s['tp2']:.4f} | TP3: {s['tp3']:.4f}
⏱ Timeframes: 1H={s['tf']['1H']}, 4H={s['tf']['4H']}, 1D={s['tf']['1D']}
⚠️ Not financial advice.
"""
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Amfani: /broadcast saƙonka")
        return
    msg = " ".join(context.args)
    await context.bot.send_message(CHANNEL_USERNAME, msg)
    await update.message.reply_text("✅ An aika broadcast!")

# ================= MAIN =================
async def main():
    print("Dynamic Auto Signal Bot PRO FINAL yana gudana...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # JobQueue for auto-post every 4H
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_scan_and_post(app)),
                                interval=14400, first=10)  # 4H

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
