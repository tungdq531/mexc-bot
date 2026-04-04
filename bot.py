import asyncio
import aiohttp
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import time

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8773493912:AAHPxOkxd_x7Pd5LhuEmzKaZEIQxRTeaP8Y"  # THAY TOKEN CỦA BẠN
CHAT_ID = "1728319803"  # THAY CHAT_ID CỦA BẠN

# Dữ liệu lưu trữ
tracked_coins = {}
alerts = {}

# ==================== HÀM LẤY GIÁ ====================
async def get_price(symbol):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                return None
    except:
        return None

# ==================== LỆNH BOT ====================
async def start(update, context):
    keyboard = [
        [("/start", "🚀 Bắt đầu")],
        [("/add", "➕ Thêm coin"), ("/list", "📋 Danh sách")],
        [("/alert", "⚠️ Tạo cảnh báo"), ("/alerts", "🔔 Xem cảnh báo")],
        [("/reset", "🔄 Reset dữ liệu"), ("/help", "❓ Trợ giúp")]
    ]
    await update.message.reply_text(
        "🤖 <b>BOT CẢNH BÁO GIÁ MEXC</b>\n\n"
        "📌 <b>LỆNH:</b>\n"
        "/add BTCUSDT - Thêm coin\n"
        "/list - Xem danh sách\n"
        "/alert BTCUSDT 5 10 - Cảnh báo 5% trong 10 phút\n"
        "/alerts - Xem cảnh báo\n"
        "/remove_alert &lt;id&gt; - Xóa cảnh báo\n"
        "/reset - Reset toàn bộ\n"
        "/help - Hướng dẫn",
        parse_mode='HTML'
    )

async def help_command(update, context):
    await update.message.reply_text(
        "📖 <b>HƯỚNG DẪN CHI TIẾT</b>\n\n"
        "<b>1. Thêm coin theo dõi:</b>\n"
        "/add BTCUSDT\n\n"
        "<b>2. Xem danh sách coin:</b>\n"
        "/list\n\n"
        "<b>3. Tạo cảnh báo biến động giá:</b>\n"
        "/alert BTCUSDT 5 10\n"
        "→ Cảnh báo khi BTC tăng/giảm 5% trong 10 phút\n\n"
        "<b>4. Xem danh sách cảnh báo:</b>\n"
        "/alerts\n\n"
        "<b>5. Xóa cảnh báo:</b>\n"
        "/remove_alert 1734567890\n\n"
        "<b>6. Reset toàn bộ dữ liệu:</b>\n"
        "/reset",
        parse_mode='HTML'
    )

async def add_coin(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ Cú pháp: /add BTCUSDT")
        return
    symbol = context.args[0].upper()
    price = await get_price(symbol)
    if not price:
        await update.message.reply_text(f"❌ Không tìm thấy {symbol} trên MEXC")
        return
    tracked_coins[symbol] = price
    await update.message.reply_text(
        f"✅ Đã thêm {symbol}\n💰 Giá: {price:,.2f} USDT"
    )

async def list_coins(update, context):
    if not tracked_coins:
        await update.message.reply_text("📭 Chưa có coin. Dùng /add để thêm.")
        return
    msg = "📋 <b>DANH SÁCH COIN</b>\n\n"
    for symbol in tracked_coins:
        current = await get_price(symbol)
        if current:
            msg += f"💰 {symbol}: {current:,.2f} USDT\n"
        else:
            msg += f"❌ {symbol}: Lỗi lấy giá\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def add_alert(update, context):
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ Cú pháp: /alert BTCUSDT 5 10")
        return
    symbol = context.args[0].upper()
    percent = float(context.args[1])
    minutes = int(context.args[2])
    
    current_price = await get_price(symbol)
    if not current_price:
        await update.message.reply_text(f"❌ Không tìm thấy {symbol}")
        return
    
    alert_id = str(int(time.time()))
    alerts[alert_id] = {
        'symbol': symbol,
        'percent': percent,
        'minutes': minutes,
        'base_price': current_price,
        'created_at': datetime.now()
    }
    await update.message.reply_text(
        f"✅ Đã tạo cảnh báo\n\n"
        f"📊 {symbol}\n"
        f"⚠️ {percent}% trong {minutes} phút\n"
        f"💰 {current_price:,.2f} USDT\n\n"
        f"🆔 ID: <code>{alert_id}</code>",
        parse_mode='HTML'
    )

async def list_alerts(update, context):
    if not alerts:
        await update.message.reply_text("📭 Chưa có cảnh báo nào.")
        return
    msg = "🔔 <b>DANH SÁCH CẢNH BÁO</b>\n\n"
    for aid, alert in alerts.items():
        time_left = alert['minutes'] - (datetime.now() - alert['created_at']).total_seconds() / 60
        msg += f"🆔 <code>{aid}</code>\n"
        msg += f"📊 {alert['symbol']} | {alert['percent']}% / {alert['minutes']}p\n"
        msg += f"💰 {alert['base_price']:,.2f} USDT\n"
        msg += f"⏰ Còn: {int(time_left)} phút\n"
        msg += "➖➖➖➖➖➖\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def remove_alert(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ /remove_alert 1734567890")
        return
    alert_id = context.args[0]
    if alert_id in alerts:
        del alerts[alert_id]
        await update.message.reply_text(f"✅ Đã xóa cảnh báo {alert_id}")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy {alert_id}")

async def reset_all(update, context):
    global tracked_coins, alerts
    tracked_coins = {}
    alerts = {}
    await update.message.reply_text("🔄 Đã reset toàn bộ dữ liệu!")

# ==================== KIỂM TRA CẢNH BÁO ====================
async def check_alerts():
    bot = Bot(token=BOT_TOKEN)
    while True:
        try:
            expired = []
            for aid, alert in alerts.items():
                time_passed = datetime.now() - alert['created_at']
                if time_passed > timedelta(minutes=alert['minutes']):
                    expired.append(aid)
                    continue
                
                current = await get_price(alert['symbol'])
                if current:
                    change = abs((current - alert['base_price']) / alert['base_price']) * 100
                    if change >= alert['percent']:
                        direction = "📈 TĂNG" if current > alert['base_price'] else "📉 GIẢM"
                        msg = (
                            f"🚨 <b>CẢNH BÁO GIÁ</b>\n\n"
                            f"📊 <b>{alert['symbol']}</b>\n"
                            f"{direction} <b>{change:.2f}%</b>\n\n"
                            f"💰 {alert['base_price']:,.2f} → {current:,.2f} USDT"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
                        expired.append(aid)
            
            for aid in expired:
                if aid in alerts:
                    del alerts[aid]
                    
        except Exception as e:
            print(f"Lỗi: {e}")
        await asyncio.sleep(30)

# ==================== CHẠY BOT ====================
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_coin))
    app.add_handler(CommandHandler("list", list_coins))
    app.add_handler(CommandHandler("alert", add_alert))
    app.add_handler(CommandHandler("alerts", list_alerts))
    app.add_handler(CommandHandler("remove_alert", remove_alert))
    app.add_handler(CommandHandler("reset", reset_all))
    
    asyncio.create_task(check_alerts())
    
    print("🤖 Bot đang chạy...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())