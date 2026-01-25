import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

TIMEFRAME = Interval.INTERVAL_4_HOURS

# 100+ coins starter pack
COINS = set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT"
])

COINS = sorted(COINS)

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
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=TIMEFRAME
    )

    analysis = handler.get_analysis()
    summary = analysis.summary

    rec_tv = summary["RECOMMENDATION"]
    buy = summary["BUY"]
    sell = summary["SELL"]
    neutral = summary["NEUTRAL"]

    price = float(analysis.indicators["close"])

    # Smart RR
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
        "buy": buy,
        "sell": sell,
        "neutral": neutral
    }

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
        "Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nZaɓi coin ko ka rubuta sunansa:",
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
        try:
            s = get_signal(symbol)

            text = f"""
📊 Signal for {s['symbol']} (4H)

📈 Recommendation: {s['rec']}

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}

💰 Take Profit 1: {s['tp1']:.4f}
💰 Take Profit 2: {s['tp2']:.4f}
💰 Take Profit 3: {s['tp3']:.4f}

🟢 Buy: {s['buy']}
🔴 Sell: {s['sell']}
⚪ Neutral: {s['neutral']}

⚠️ Not financial advice.
"""
            await query.edit_message_text(text)
        except:
            await query.edit_message_text("❌ An samu matsala wajen ɗauko signal.")

# ================= SEARCH =================
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

        # auto add to whitelist
        if text not in COINS:
            COINS.append(text)
            COINS.sort()

        msg = f"""
📊 Signal for {s['symbol']} (4H)

📈 Recommendation: {s['rec']}

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}

💰 Take Profit 1: {s['tp1']:.4f}
💰 Take Profit 2: {s['tp2']:.4f}
💰 Take Profit 3: {s['tp3']:.4f}

🟢 Buy: {s['buy']}
🔴 Sell: {s['sell']}
⚪ Neutral: {s['neutral']}

⚠️ Not financial advice.
"""
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

# ================= MAIN =================
def main():
    print("Dynamic Auto Signal Bot PRO yana gudana...")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    app.run_polling()

if __name__ == "__main__":
    main()
