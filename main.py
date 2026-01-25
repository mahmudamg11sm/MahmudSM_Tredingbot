import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval
from dotenv import load_dotenv
import nest_asyncio

# ========== LOAD ENV ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

# ========== CONFIG ==========
TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

# 100+ coins
COINS = sorted(set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT"
]))

logging.basicConfig(level=logging.INFO)
nest_asyncio.apply()  # Fix asyncio loop issues

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
    strong_only = False

    for tf_name, tf_interval in TIMEFRAMES.items():
        handler = TA_Handler(symbol=symbol, screener="crypto", exchange="BYBIT", interval=tf_interval)
        analysis = handler.get_analysis()
        rec = analysis.summary["RECOMMENDATION"]
        results[tf_name] = rec
        if rec in ["STRONG_BUY", "STRONG_SELL"]:
            strong_only = True

    # Get current price
    price = float(handler.get_analysis().indicators["close"])

    # Default values
    rec_tv = results["4H"]
    if rec_tv in ["BUY","STRONG_BUY"]:
        rec = "BUY"
        entry = price
        sl = price * 0.97
        tp1, tp2, tp3 = price*1.05, price*1.12, price*1.30
    elif rec_tv in ["SELL","STRONG_SELL"]:
        rec = "SELL"
        entry = price
        sl = price * 1.03
        tp1, tp2, tp3 = price*0.95, price*0.88, price*0.70
    else:
        rec = "NEUTRAL"
        entry = price
        sl = price * 0.99
        tp1, tp2, tp3 = price*1.01, price*1.02, price*1.03

    return {
        "symbol": symbol,
        "rec": rec,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "results": results,
        "strong_only": strong_only
    }

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Na shiga", callback_data="check_join")]
        ])
        await update.message.reply_text(f"Don amfani da bot, sai ka shiga channel ɗinmu:\n{CHANNEL_USERNAME}", reply_markup=btn)
        return

    await update.message.reply_text("Barka da zuwa Dynamic Auto Signal Bot 🚀\n\nZaɓi coin ko ka rubuta sunansa:", reply_markup=coins_keyboard(0))

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
            if not s["strong_only"]:
                await query.edit_message_text(f"⚠️ Signal for {symbol} is not STRONG. Skipped.")
                return

            text = f"""
📊 Signal for {s['symbol']} (4H Strong)

📈 Recommendation: {s['rec']}
🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 Take Profit 1: {s['tp1']:.4f}
💰 Take Profit 2: {s['tp2']:.4f}
💰 Take Profit 3: {s['tp3']:.4f}

1H: {s['results']['1H']}
4H: {s['results']['4H']}
1D: {s['results']['1D']}

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
        if not s["strong_only"]:
            await update.message.reply_text(f"⚠️ Signal for {text} is not STRONG. Skipped.")
            return

        msg = f"""
📊 Signal for {s['symbol']} (4H Strong)

📈 Recommendation: {s['rec']}
🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 Take Profit 1: {s['tp1']:.4f}
💰 Take Profit 2: {s['tp2']:.4f}
💰 Take Profit 3: {s['tp3']:.4f}

1H: {s['results']['1H']}
4H: {s['results']['4H']}
1D: {s['results']['1D']}

⚠️ Not financial advice.
"""
        await update.message.reply_text(msg)

        if text not in COINS:
            COINS.append(text)
            COINS.sort()
    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

# ================= AUTO 4H POST =================
async def auto_scan_and_post(app):
    for coin in COINS:
        try:
            s = get_signal(coin)
            if s["strong_only"]:
                msg = f"🔔 Auto 4H Strong Signal\n\n📊 {s['symbol']}\n📈 {s['rec']}\n🎯 Entry: {s['entry']:.4f}\n🛑 SL: {s['sl']:.4f}\n💰 TP1: {s['tp1']:.4f}\n💰 TP2: {s['tp2']:.4f}\n💰 TP3: {s['tp3']:.4f}"
                await app.bot.send_message(CHANNEL_USERNAME, msg)
        except:
            continue

# ================= MAIN =================
async def main():
    print("Dynamic Auto Signal Bot PRO FINAL yana gudana...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # Auto 4H Strong signals
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_scan_and_post(app)), interval=14400, first=10)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
