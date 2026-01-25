import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from tradingview_ta import TA_Handler, Interval

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6648308251"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Mahmudsm1")
TIMEFRAMES = [Interval.INTERVAL_1_HOUR, Interval.INTERVAL_4_HOURS, Interval.INTERVAL_1_DAY]

logging.basicConfig(level=logging.INFO)

# 100+ coins whitelist
COINS = sorted(list(set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT"
])))

# ================= GLOBALS =================
SIGNAL_HISTORY = []
WINRATE = {}

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
    for i, coin in enumerate(chunk,1):
        row.append(InlineKeyboardButton(coin.replace("USDT",""), callback_data=f"coin:{coin}"))
        if i % 3 == 0:
            keyboard.append(row)
            row=[]
    if row:
        keyboard.append(row)

    nav=[]
    if start>0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if end<len(COINS): nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))
    if nav: keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

# ================= SIGNAL =================
def get_signal(symbol:str, timeframe=Interval.INTERVAL_4_HOURS):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=timeframe
    )
    analysis = handler.get_analysis()
    summary = analysis.summary

    rec_tv = summary["RECOMMENDATION"]
    buy = summary["BUY"]
    sell = summary["SELL"]
    neutral = summary["NEUTRAL"]

    price = float(analysis.indicators["close"])

    # Only strong signals
    if rec_tv in ["STRONG_BUY"]:
        rec = "BUY"
        entry = price
        sl = price*0.97
        tp1,tp2,tp3 = price*1.05, price*1.12, price*1.30
    elif rec_tv in ["STRONG_SELL"]:
        rec = "SELL"
        entry = price
        sl = price*1.03
        tp1,tp2,tp3 = price*0.95, price*0.88, price*0.70
    else:
        rec="NEUTRAL"
        entry=price
        sl=price*0.99
        tp1,tp2,tp3 = price*1.01, price*1.02, price*1.03

    return {"symbol":symbol,"rec":rec,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,
            "buy":buy,"sell":sell,"neutral":neutral}

# ================= WINRATE =================
def update_winrate(signal, current_price):
    sym = signal["symbol"]
    if sym not in WINRATE: WINRATE[sym]={"win":0,"loss":0}
    if signal["rec"]=="BUY":
        if current_price>=signal["tp1"]: WINRATE[sym]["win"]+=1
        elif current_price<=signal["sl"]: WINRATE[sym]["loss"]+=1
    elif signal["rec"]=="SELL":
        if current_price<=signal["tp1"]: WINRATE[sym]["win"]+=1
        elif current_price>=signal["sl"]: WINRATE[sym]["loss"]+=1

def save_signal_history(signal):
    SIGNAL_HISTORY.append({
        "symbol":signal["symbol"],"rec":signal["rec"],
        "entry":signal["entry"],"sl":signal["sl"],
        "tp1":signal["tp1"],"tp2":signal["tp2"],"tp3":signal["tp3"],
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

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

# ================= CALLBACKS =================
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
            save_signal_history(s)
            text = f"""📊 {s['rec']} STRONG Signal for {s['symbol']} (4H)
🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 TP1:{s['tp1']:.4f} TP2:{s['tp2']:.4f} TP3:{s['tp3']:.4f}
🟢 Buy:{s['buy']} 🔴 Sell:{s['sell']} ⚪ Neutral:{s['neutral']}
⚠️ Not financial advice."""
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
    if not text.endswith("USDT"): text+="USDT"
    try:
        s = get_signal(text)
        if text not in COINS:
            COINS.append(text)
            COINS.sort()
        save_signal_history(s)
        msg = f"""📊 {s['rec']} STRONG Signal for {s['symbol']} (4H)
🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}
💰 TP1:{s['tp1']:.4f} TP2:{s['tp2']:.4f} TP3:{s['tp3']:.4f}
🟢 Buy:{s['buy']} 🔴 Sell:{s['sell']} ⚪ Neutral:{s['neutral']}
⚠️ Not financial advice."""
        await update.message.reply_text(msg)
    except:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")

# ================= ADMIN =================
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(f"Channel: {CHANNEL_USERNAME}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg=" ".join(context.args)
    if not msg: await update.message.reply_text("Rubuta sako bayan /broadcast"); return
    try: await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=msg); await update.message.reply_text("✅ An tura sakon")
    except Exception as e: await update.message.reply_text(f"❌ An samu matsala: {e}")

# ================= AUTO POST =================
async def auto_scan_and_post(app: Application):
    for coin in COINS:
        s = get_signal(coin)
        if s["rec"] not in ["BUY","SELL"]: continue
        save_signal_history(s)
        text = f"""📊 4H STRONG Signal for {s['symbol']}
📈 Recommendation: {s['rec']}
🎯 Entry:{s['entry']:.4f} 🛑 SL:{s['sl']:.4f}
💰 TP1:{s['tp1']:.4f} TP2:{s['tp2']:.4f} TP3:{s['tp3']:.4f}
🟢 Buy:{s['buy']} 🔴 Sell:{s['sell']} ⚪ Neutral:{s['neutral']}
⚠️ Not financial advice."""
        try: await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
        except: continue
        update_winrate(s, s["entry"])

# ================= MAIN =================
async def main():
    print("Dynamic Auto Signal Bot PRO FINAL yana gudana...")
    app = Application.builder().token(BOT_TOKEN).build()
    # commands & callbacks
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))
    # admin
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("broadcast", broadcast))
    # job queue every 4H
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_scan_and_post(app)), interval=14400, first=10)
    await app.run_polling()

if __name__=="__main__":
    asyncio.run(main())
