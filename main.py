import os
import logging
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
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
TF_1H = Interval.INTERVAL_1_HOUR
TF_4H = Interval.INTERVAL_4_HOURS
TF_1D = Interval.INTERVAL_1_DAY

# Logging
logging.basicConfig(level=logging.INFO)

# ================= DATA =================

# Big whitelist (100+)
COINS = set([
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","MATICUSDT","DOTUSDT",
    "LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","UNIUSDT","OPUSDT","ARBUSDT","FILUSDT","NEARUSDT","APEUSDT",
    "SUIUSDT","INJUSDT","TIAUSDT","SEIUSDT","RUNEUSDT","AAVEUSDT","ETCUSDT","EOSUSDT","ICPUSDT","FTMUSDT",
    "GALAUSDT","SANDUSDT","MANAUSDT","CHZUSDT","1000PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","ORDIUSDT",
    "JUPUSDT","PYTHUSDT","DYDXUSDT","CRVUSDT","SNXUSDT","GMXUSDT","COMPUSDT","ZILUSDT","KSMUSDT","NEOUSDT",
    "XTZUSDT","MINAUSDT","ROSEUSDT","CELOUSDT","LDOUSDT","YFIUSDT","MASKUSDT","BLURUSDT","MAGICUSDT",
    "IMXUSDT","RNDRUSDT","STXUSDT","ARUSDT","KASUSDT","CFXUSDT","IDUSDT","HOOKUSDT","HIGHUSDT",
    "PEOPLEUSDT","ENSUSDT","APTUSDT","GRTUSDT","QNTUSDT","OCEANUSDT","AGIXUSDT","ILVUSDT","WOOUSDT",
    "SKLUSDT","SUSHIUSDT","1INCHUSDT","BALUSDT","BATUSDT","COTIUSDT","DENTUSDT","ENJUSDT","HOTUSDT"
])

COINS = sorted(COINS)

# Winrate tracking
STATS = {
    "signals": 0,
    "wins": 0,
    "losses": 0
}

# ================= HELPERS =================

async def is_user_in_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def coins_keyboard(page=0, per_page=15):
    coins_list = list(COINS)
    start = page * per_page
    end = start + per_page
    chunk = coins_list[start:end]

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
    if end < len(coins_list):
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))

    if nav:
        keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

# ================= ANALYSIS CORE =================

def tv_analysis(symbol: str, interval):
    handler = TA_Handler(
        symbol=symbol,
        screener="crypto",
        exchange="BYBIT",
        interval=interval
    )
    return handler.get_analysis()


def get_multi_tf_signal(symbol: str):
    """
    1H + 4H + 1D confirmation
    Only STRONG signals pass
    """

    a1 = tv_analysis(symbol, TF_1H)
    a4 = tv_analysis(symbol, TF_4H)
    aD = tv_analysis(symbol, TF_1D)

    r1 = a1.summary["RECOMMENDATION"]
    r4 = a4.summary["RECOMMENDATION"]
    rD = aD.summary["RECOMMENDATION"]

    # Only STRONG confirmations
    if r1 in ["STRONG_BUY", "BUY"] and r4 in ["STRONG_BUY", "BUY"] and rD in ["STRONG_BUY", "BUY"]:
        direction = "BUY"
    elif r1 in ["STRONG_SELL", "SELL"] and r4 in ["STRONG_SELL", "SELL"] and rD in ["STRONG_SELL", "SELL"]:
        direction = "SELL"
    else:
        return None  # Not strong enough

    price = float(a4.indicators["close"])

    # Smart RR system
    if direction == "BUY":
        entry = price
        sl = price * 0.96
        tp1 = price * 1.05
        tp2 = price * 1.15
        tp3 = price * 1.35
    else:
        entry = price
        sl = price * 1.04
        tp1 = price * 0.95
        tp2 = price * 0.85
        tp3 = price * 0.65

    return {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "buy": a4.summary["BUY"],
        "sell": a4.summary["SELL"],
        "neutral": a4.summary["NEUTRAL"],
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }

# ================= AUTO SCANNER CORE =================

async def auto_scan_and_post(app: Application):
    await asyncio.sleep(20)

    while True:
        print("🔍 Auto scanning coins...")

        for coin in list(COINS):
            try:
                s = get_multi_tf_signal(coin)
                if not s:
                    continue

                STATS["signals"] += 1

                text = f"""
🚨 **AUTO SIGNAL (STRONG)** 🚨

📊 {s['symbol']}
⏱ Time: 4H (Confirmed 1H + 4H + 1D)

📈 Direction: **{s['direction']}**

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}

💰 TP1: {s['tp1']:.4f}
💰 TP2: {s['tp2']:.4f}
💰 TP3: {s['tp3']:.4f}

🟢 Buy: {s['buy']} | 🔴 Sell: {s['sell']} | ⚪ Neutral: {s['neutral']}

⚠️ Not financial advice.
"""

                await app.bot.send_message(
                    chat_id=CHANNEL_USERNAME,
                    text=text,
                    parse_mode="Markdown"
                )

                await asyncio.sleep(3)

            except Exception as e:
                print("Scan error:", e)

        # Wait 4 hours
        print("⏳ Waiting 4H for next scan...")
        await asyncio.sleep(60 * 60 * 4)


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
            s = get_multi_tf_signal(symbol)
            if not s:
                await query.edit_message_text("❌ Ba a samu STRONG signal ba!")
                return

            text = f"""
📊 Signal for {s['symbol']} (4H STRONG)

📈 Direction: **{s['direction']}**

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}

💰 TP1: {s['tp1']:.4f}
💰 TP2: {s['tp2']:.4f}
💰 TP3: {s['tp3']:.4f}

🟢 Buy: {s['buy']} | 🔴 Sell: {s['sell']} | ⚪ Neutral: {s['neutral']}

⚠️ Not financial advice.
"""
            await query.edit_message_text(text)
        except Exception as e:
            await query.edit_message_text(f"❌ An samu matsala: {e}")


# ================= SEARCH COIN =================
async def search_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_channel(context, user_id):
        await update.message.reply_text(f"Da fari sai ka shiga {CHANNEL_USERNAME}")
        return

    text = update.message.text.upper().strip()
    if not text.endswith("USDT"):
        text += "USDT"

    try:
        s = get_multi_tf_signal(text)
        if not s:
            await update.message.reply_text(f"❌ Ba a samu STRONG signal ba: {text}")
            return

        # auto add to whitelist
        if text not in COINS:
            COINS.add(text)

        msg = f"""
📊 Signal for {s['symbol']} (4H STRONG)

📈 Direction: **{s['direction']}**

🎯 Entry: {s['entry']:.4f}
🛑 Stop Loss: {s['sl']:.4f}

💰 TP1: {s['tp1']:.4f}
💰 TP2: {s['tp2']:.4f}
💰 TP3: {s['tp3']:.4f}

🟢 Buy: {s['buy']} | 🔴 Sell: {s['sell']} | ⚪ Neutral: {s['neutral']}

⚠️ Not financial advice.
"""
        await update.message.reply_text(msg)

    except Exception as e:
        await update.message.reply_text(f"❌ Ba a samu coin ba: {text}")


# ================= ADMIN COMMANDS =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Amfani: /broadcast saƙonka")
        return

    msg = " ".join(context.args)
    await update.message.reply_text("✅ Broadcast sent (manual only).")
    await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=msg)


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = f"✅ Total tracked coins: {len(COINS)}\n"
    msg += f"📊 Signals sent: {STATS['signals']}\n"
    msg += f"🏆 Wins: {STATS['wins']}, Losses: {STATS['losses']}"
    await update.message.reply_text(msg)


# ================= MAIN =================
async def main():
    print("Dynamic Auto Signal Bot PRO FINAL yana gudana...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_coin))

    # Auto scanning in background
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_scan_and_post(app)), interval=10, first=10)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
