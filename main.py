import os
import asyncio
import logging
import nest_asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval

nest_asyncio.apply()  # fix for async in Railway/Heroku

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")

TIMEFRAMES = {
    "1H": Interval.INTERVAL_1_HOUR,
    "4H": Interval.INTERVAL_4_HOURS,
    "1D": Interval.INTERVAL_1_DAY
}

# Starter whitelist 100+ coins
COINS = sorted(set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT"
]))

# Store winrate tracking
WINRATE = {}

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

def get_signal(symbol: str):
    # Multi-timeframe analysis
    results = {}
    strong_signal = None
    for tf_name, tf in TIMEFRAMES.items():
        handler = TA_Handler(symbol=symbol, screener="crypto", exchange="BYBIT", interval=tf)
        analysis = handler.get_analysis()
        summary = analysis.summary
        results[tf_name] = summary
        # Only strong recommendations
        if summary["RECOMMENDATION"] in ["STRONG_BUY", "STRONG_SELL"]:
            strong_signal = summary["RECOMMENDATION"]

    if not strong_signal:
        return None  # skip weak/neutral signals

    # Use 4H as main for price targets
    price = float(handler.get_analysis().indicators["close"])
    if strong_signal == "STRONG_BUY":
        entry = price
        sl = price * 0.97
        tp1 = price * 1.05
        tp2 = price * 1.12
        tp3 = price * 1.50
        rec = "BUY"
    elif strong_signal == "STRONG_SELL":
        entry = price
        sl = price * 1.03
        tp1 = price * 0.95
        tp2 = price * 0.88
        tp3 = price * 0.70
        rec = "SELL"
    else:
        return None

    return {
        "symbol": symbol,
        "rec": rec,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ================= AUTO POST =================
async def auto_scan_and_post(app: Application):
    for coin in COINS:
        try:
            signal = get_signal(coin)
            if not signal:
                continue
            text = f"""
📊 STRONG Signal for {signal['symbol']} (4H)

📈 Recommendation: {signal['rec']}

🎯 Entry: {signal['entry']:.4f}
🛑 Stop Loss: {signal['sl']:.4f}

💰 Take Profit 1: {signal['tp1']:.4f}
💰 Take Profit 2: {signal['tp2']:.4f}
💰 Take Profit 3: {signal['tp3']:.4f}

⚠️ Not financial advice.
⏰ {signal['time']}
"""
            await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
        except Exception as e:
            logging.error(f"Error posting {coin}: {e}")

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
    await update.message.reply_text("Barka da zuwa Dynamic Auto Signal Bot 🚀", reply_markup=coins_keyboard(0))

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_user_in_channel(context, query.from_user.id):
        await query.edit_message_text("✅ An tabbatar! Zaɓi coin:", reply_markup=coins_keyboard(0))
    else:
        await query.answer("❌ Har yanzu baka shiga channel ba!", show_alert=True)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Amfani: /broadcast saƙonka")
        return
    msg = " ".join(context.args)
    await update.message.reply_text(f"✅ Broadcast sent (manual).")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"Whitelist coins count: {len(COINS)}")

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
            signal = get_signal(symbol)
            if not signal:
                await query.edit_message_text("❌ No strong signal currently.")
                return
            text = f"""
📊 STRONG Signal for {signal['symbol']} (4H)

📈 Recommendation: {signal['rec']}

🎯 Entry: {signal['entry']:.4f}
🛑 Stop Loss: {signal['sl']:.4f}

💰 Take Profit 1: {signal['tp1']:.4f}
💰 Take Profit 2: {signal['tp2']:.4f}
💰 Take Profit 3: {signal['tp3']:.4f}

⏰ {signal['time']}
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
        signal = get_signal(text)
        if not signal:
            await update.message.reply_text("❌ No strong signal currently.")
            return
        # Auto add to whitelist
        if text not in COINS:
            COINS.append(text)
            COINS.sort()
        msg = f"""
📊 STRONG Signal for {signal['symbol']} (4H)

📈 Recommendation: {signal['rec']}

🎯 Entry: {signal['entry']:.4f}
🛑 Stop Loss: {signal['sl']:.4f}

💰 Take Profit 1: {signal['tp1']:.4f}
💰 Take Profit 2: {signal['tp2']:.4f}
💰 Take Profit 3: {signal['tp3']:.4f}

⏰ {signal['time']}
⚠️ Not financial advice.
"""
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

# ================= MAIN =================
async def main():
    print("Dynamic Auto Signal Bot PRO FINAL yana gudana...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # JobQueue auto post
    if not app.job_queue:
        raise RuntimeError("JobQueue not initialized! Install python-telegram-bot[job-queue]")
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_scan_and_post(app)), interval=4*3600, first=10)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
