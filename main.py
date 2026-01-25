import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

# Timeframes
TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

# Coins
COINS = sorted([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
    "AVAXUSDT","MATICUSDT","DOTUSDT","LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT",
    "UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT","SUIUSDT","INJUSDT"
])

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
def get_signal(symbol: str, timeframe: str, only_strong=False):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=TIMEFRAMES[timeframe]
    )
    analysis = handler.get_analysis()
    summary = analysis.summary
    rec_tv = summary["RECOMMENDATION"]

    if only_strong and rec_tv not in ["STRONG_BUY", "STRONG_SELL"]:
        raise ValueError(f"Signal for {symbol} ({timeframe}) is not STRONG. Skipped.")

    price = float(analysis.indicators["close"])

    if rec_tv in ["BUY", "STRONG_BUY"]:
        rec = "BUY"
        entry = price
        sl = price * 0.97
        tp1 = price * 1.05
        tp2 = price * 1.12
        tp3 = price * 1.30
    elif rec_tv in ["SELL", "STRONG_SELL"]:
        rec = "SELL"
        entry = price
        sl = price * 1.03
        tp1 = price * 0.95
        tp2 = price * 0.88
        tp3 = price * 0.70
    else:
        rec = "NEUTRAL"
        entry = price
        sl = price * 0.99
        tp1 = price * 1.01
        tp2 = price * 1.02
        tp3 = price * 1.03

    return {
        "symbol": symbol,
        "rec": rec,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "buy": summary["BUY"],
        "sell": summary["SELL"],
        "neutral": summary["NEUTRAL"],
        "raw_rec": rec_tv
    }

def format_signal_text(signal: dict, timeframe: str):
    return f"""
📊 Signal for {signal['symbol']} ({timeframe})

📈 Recommendation: {signal['rec']}

🎯 Entry: {signal['entry']:.4f}
🛑 Stop Loss: {signal['sl']:.4f}

💰 Take Profit 1: {signal['tp1']:.4f}
💰 Take Profit 2: {signal['tp2']:.4f}
💰 Take Profit 3: {signal['tp3']:.4f}

🟢 Buy: {signal['buy']}
🔴 Sell: {signal['sell']}
⚪ Neutral: {signal['neutral']}

⚠️ Not financial advice.
"""

# ================= AUTO POST =================
async def auto_scan_and_post(app):
    for symbol in COINS:
        try:
            s4h = get_signal(symbol, "4H", only_strong=True)  # STRONG only
            text = format_signal_text(s4h, "4H")
            await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
            logging.info(f"Posted {symbol} 4H STRONG signal")
        except Exception as e:
            logging.info(str(e))

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Na shiga", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"Don amfani da bot, sai ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}",
            reply_markup=btn
        )
        return

    await update.message.reply_text(
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\nZaɓi coin ko ka rubuta sunansa:",
        reply_markup=coins_keyboard(0)
    )

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_in_channel(context, query.from_user.id):
        await query.edit_message_text("✅ An tabbatar! Zaɓi coin:", reply_markup=coins_keyboard(0))
    else:
        await query.answer("❌ Har yanzu baka shiga channel ba!", show_alert=True)

# ================= CALLBACK =================
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
        msg_list = []
        for tf in ["1H","4H","1D"]:
            try:
                s = get_signal(symbol, tf, only_strong=False)  # All signals
                msg_list.append(format_signal_text(s, tf))
            except:
                msg_list.append(f"❌ Ba a samu signal ba: {symbol} ({tf})")
        await query.edit_message_text("\n\n".join(msg_list))

# ================= SEARCH =================
async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Da fari sai ka shiga {CHANNEL_USERNAME}")
        return

    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"

    msg_list = []
    for tf in ["1H","4H","1D"]:
        try:
            s = get_signal(text, tf, only_strong=False)
            msg_list.append(format_signal_text(s, tf))
        except:
            msg_list.append(f"❌ Ba a samu signal ba: {text} ({tf})")
    await update.message.reply_text("\n\n".join(msg_list))

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # Auto post every 4H
    async def job_wrapper(context):
        await auto_scan_and_post(app)

    app.job_queue.run_repeating(job_wrapper, interval=14400, first=10)  # 4H

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
