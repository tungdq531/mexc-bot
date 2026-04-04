import requests
import time
import json
from datetime import datetime, timedelta
import threading
import re

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8773493912:AAHPxOkxd_x7Pd5LhuEmzKaZEIQxRTeaP8Y"

# Dữ liệu lưu trữ cho nhiều người dùng
user_data = {}  # {chat_id: {'coins': {}, 'alerts': {}}}

# ==================== HÀM LẤY GIÁ ====================
def get_price(symbol):
    try:
        url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

# ==================== GỬI TIN NHẮN ====================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi: {e}")

# ==================== TẠO MENU CHÍNH ====================
def get_main_keyboard():
    return {
        "keyboard": [
            ["📊 Thêm coin", "📋 Danh sách coin"],
            ["⚠️ Tạo cảnh báo", "🔔 Xem cảnh báo"],
            ["❌ Xóa cảnh báo", "🔄 Reset dữ liệu"],
            ["❓ Trợ giúp"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_back_keyboard():
    return {
        "keyboard": [["🔙 Quay lại menu chính"]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def get_alert_actions_keyboard(alert_id):
    return {
        "inline_keyboard": [
            [{"text": "✅ Xóa cảnh báo", "callback_data": f"del_{alert_id}"}],
            [{"text": "🔙 Quay lại", "callback_data": "back_alerts"}]
        ]
    }

# ==================== TẠO MENU LỆNH (GÓC DƯỚI BÊN TRÁI) ====================
def set_bot_commands():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    commands = [
        {"command": "start", "description": "🚀 Khởi động bot"},
        {"command": "menu", "description": "📋 Hiển thị menu chính"},
        {"command": "add", "description": "➕ Thêm coin theo dõi"},
        {"command": "list", "description": "📋 Xem danh sách coin"},
        {"command": "alert", "description": "⚠️ Tạo cảnh báo giá"},
        {"command": "alerts", "description": "🔔 Xem cảnh báo"},
        {"command": "remove_alert", "description": "❌ Xóa cảnh báo"},
        {"command": "reset", "description": "🔄 Reset dữ liệu"},
        {"command": "help", "description": "❓ Hướng dẫn sử dụng"}
    ]
    try:
        requests.post(url, json={"commands": commands}, timeout=10)
    except:
        pass

# ==================== XỬ LÝ LỆNH TEXT ====================
def process_command(chat_id, text):
    # Lấy hoặc tạo dữ liệu user
    if chat_id not in user_data:
        user_data[chat_id] = {'coins': {}, 'alerts': {}}
    
    user = user_data[chat_id]
    text = text.strip()
    
    # Xử lý menu text
    if text == "🔙 Quay lại menu chính" or text == "/menu":
        send_message(chat_id, "📋 <b>MENU CHÍNH</b>\n\nChọn chức năng:", get_main_keyboard())
        return
    
    if text == "📊 Thêm coin" or text == "/add":
        send_message(chat_id, "💰 <b>THÊM COIN</b>\n\nVui lòng nhập mã coin:\n\n<i>Ví dụ: BTCUSDT, ETHUSDT</i>\n\nHoặc gõ /cancel để hủy.", get_back_keyboard())
        return
    
    if text == "📋 Danh sách coin" or text == "/list":
        if not user['coins']:
            send_message(chat_id, "📭 Chưa có coin nào.\n\nDùng nút '📊 Thêm coin' để thêm.", get_main_keyboard())
            return
        msg = "📋 <b>DANH SÁCH COIN THEO DÕI</b>\n\n"
        for symbol, base_price in user['coins'].items():
            current = get_price(symbol)
            if current:
                change = ((current - base_price) / base_price) * 100
                arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                msg += f"{arrow} <b>{symbol}</b>: {current:,.5f} USDT ({change:+.2f}%)\n"
            else:
                msg += f"❌ <b>{symbol}</b>: Không lấy được giá\n"
        send_message(chat_id, msg, get_main_keyboard())
        return
    
    if text == "⚠️ Tạo cảnh báo" or text == "/alert":
        send_message(chat_id, "⚠️ <b>TẠO CẢNH BÁO</b>\n\nVui lòng nhập theo cú pháp:\n\n<code>COIN % PHÚT</code>\n\n<i>Ví dụ: BTCUSDT 5 10</i>\n(Cảnh báo khi BTC biến động 5% trong 10 phút)\n\nHoặc gõ /cancel để hủy.", get_back_keyboard())
        return
    
    if text == "🔔 Xem cảnh báo" or text == "/alerts":
        if not user['alerts']:
            send_message(chat_id, "🔔 Chưa có cảnh báo nào.\n\nDùng nút '⚠️ Tạo cảnh báo' để tạo.", get_main_keyboard())
            return
        msg = "🔔 <b>DANH SÁCH CẢNH BÁO</b>\n\n"
        for aid, alert in user['alerts'].items():
            remaining = alert['minutes'] - (datetime.now() - alert['created_at']).total_seconds() / 60
            msg += f"🆔 <code>{aid}</code>\n"
            msg += f"📊 {alert['symbol']} | {alert['percent']}% / {alert['minutes']}p\n"
            msg += f"💰 {alert['base_price']:,.5f} USDT\n"
            msg += f"⏰ Còn: {max(0, int(remaining))} phút\n"
            msg += "➖➖➖➖➖➖\n"
        send_message(chat_id, msg, get_main_keyboard())
        return
    
    if text == "❌ Xóa cảnh báo" or text == "/remove_alert":
        if not user['alerts']:
            send_message(chat_id, "📭 Không có cảnh báo nào để xóa.", get_main_keyboard())
            return
        msg = "❌ <b>CHỌN CẢNH BÁO CẦN XÓA</b>\n\n"
        for aid, alert in user['alerts'].items():
            msg += f"🆔 <code>{aid}</code> - {alert['symbol']} | {alert['percent']}% / {alert['minutes']}p\n"
        msg += "\nNhập ID cảnh báo cần xóa:\n<i>Ví dụ: 1734567890</i>\n\nHoặc gõ /cancel để hủy."
        send_message(chat_id, msg, get_back_keyboard())
        return
    
    if text == "🔄 Reset dữ liệu" or text == "/reset":
        user['coins'] = {}
        user['alerts'] = {}
        send_message(chat_id, "🔄 Đã reset toàn bộ dữ liệu!\n\nDùng nút '📊 Thêm coin' để bắt đầu.", get_main_keyboard())
        return
    
    if text == "❓ Trợ giúp" or text == "/help":
        msg = (
            "❓ <b>HƯỚNG DẪN SỬ DỤNG</b>\n\n"
            "<b>📊 THÊM COIN</b>\n"
            "Click nút '📊 Thêm coin' hoặc gõ /add\n"
            "Nhập mã coin (VD: BTCUSDT, ETHUSDT)\n\n"
            "<b>⚠️ TẠO CẢNH BÁO</b>\n"
            "Click nút '⚠️ Tạo cảnh báo' hoặc gõ /alert\n"
            "Nhập: COIN % PHÚT (VD: BTCUSDT 5 10)\n\n"
            "<b>🔔 XEM CẢNH BÁO</b>\n"
            "Click nút '🔔 Xem cảnh báo' hoặc gõ /alerts\n\n"
            "<b>❌ XÓA CẢNH BÁO</b>\n"
            "Click nút '❌ Xóa cảnh báo' hoặc gõ /remove_alert\n"
            "Nhập ID cảnh báo cần xóa\n\n"
            "<b>🔄 RESET DỮ LIỆU</b>\n"
            "Click nút '🔄 Reset dữ liệu' hoặc gõ /reset"
        )
        send_message(chat_id, msg, get_main_keyboard())
        return
    
    if text == "/start":
        send_message(chat_id, 
            "🤖 <b>CHÀO MỪNG BẠN ĐẾN VỚI BOT CẢNH BÁO GIÁ MEXC</b>\n\n"
            "Bot giúp bạn theo dõi giá coin và nhận cảnh báo khi giá biến động.\n\n"
            "Click nút bên dưới để bắt đầu!",
            get_main_keyboard())
        return
    
    # Xử lý nhập liệu thêm coin
    if re.match(r'^[A-Z]{3,10}$', text.upper()):
        symbol = text.upper()
        price = get_price(symbol)
        if price:
            user['coins'][symbol] = price
            send_message(chat_id, f"✅ Đã thêm <b>{symbol}</b>\n💰 Giá: {price:,.5f} USDT", get_main_keyboard())
        else:
            send_message(chat_id, f"❌ Không tìm thấy coin <b>{symbol}</b>\n\nVui lòng kiểm tra lại mã coin.", get_back_keyboard())
        return
    
    # Xử lý nhập liệu tạo cảnh báo
    parts = text.split()
    if len(parts) == 3 and parts[1].replace('.', '').isdigit() and parts[2].isdigit():
        symbol = parts[0].upper()
        percent = float(parts[1])
        minutes = int(parts[2])
        price = get_price(symbol)
        if price:
            alert_id = str(int(time.time()))
            user['alerts'][alert_id] = {
                'symbol': symbol,
                'percent': percent,
                'minutes': minutes,
                'base_price': price,
                'created_at': datetime.now()
            }
            send_message(chat_id, 
                f"✅ Đã tạo cảnh báo <b>{symbol}</b>\n"
                f"⚠️ {percent}% trong {minutes} phút\n"
                f"💰 {price:,.5f} USDT\n\n"
                f"🆔 ID: <code>{alert_id}</code>", get_main_keyboard())
        else:
            send_message(chat_id, f"❌ Không tìm thấy coin <b>{symbol}</b>", get_back_keyboard())
        return
    
    # Xử lý xóa cảnh báo
    if text.isdigit() and text in user['alerts']:
        del user['alerts'][text]
        send_message(chat_id, f"✅ Đã xóa cảnh báo <code>{text}</code>", get_main_keyboard())
        return
    
    if text != "/cancel":
        send_message(chat_id, "❌ Lệnh không hợp lệ!\n\nVui lòng sử dụng menu bên dưới.", get_main_keyboard())

# ==================== XỬ LÝ CALLBACK (NHẤN NÚT INLINE) ====================
def process_callback(chat_id, data):
    if chat_id not in user_data:
        user_data[chat_id] = {'coins': {}, 'alerts': {}}
    
    if data.startswith("del_"):
        alert_id = data[4:]
        if alert_id in user_data[chat_id]['alerts']:
            del user_data[chat_id]['alerts'][alert_id]
            send_message(chat_id, f"✅ Đã xóa cảnh báo <code>{alert_id}</code>", get_main_keyboard())
        else:
            send_message(chat_id, "❌ Cảnh báo không tồn tại hoặc đã được xóa.", get_main_keyboard())
    
    elif data == "back_alerts":
        send_message(chat_id, "🔔 <b>DANH SÁCH CẢNH BÁO</b>", get_main_keyboard())

# ==================== KIỂM TRA CẢNH BÁO ====================
def alert_worker():
    while True:
        try:
            now = datetime.now()
            for chat_id, user in user_data.items():
                to_remove = []
                for aid, alert in user['alerts'].items():
                    if now - alert['created_at'] > timedelta(minutes=alert['minutes']):
                        to_remove.append(aid)
                        continue
                    current = get_price(alert['symbol'])
                    if current:
                        change = abs((current - alert['base_price']) / alert['base_price']) * 100
                        if change >= alert['percent']:
                            direction = "📈 TĂNG" if current > alert['base_price'] else "📉 GIẢM"
                            msg = (
                                f"🚨 <b>CẢNH BÁO GIÁ</b>\n\n"
                                f"📊 <b>{alert['symbol']}</b>\n"
                                f"{direction} <b>{change:.2f}%</b> (ngưỡng {alert['percent']}%)\n\n"
                                f"💰 {alert['base_price']:,.5f} → {current:,.5f} USDT"
                            )
                            send_message(chat_id, msg)
                            to_remove.append(aid)
                for aid in to_remove:
                    if aid in user['alerts']:
                        del user['alerts'][aid]
        except Exception as e:
            print(f"Lỗi cảnh báo: {e}")
        time.sleep(30)

# ==================== NHẬN TIN NHẮN ====================
def main():
    # Đặt menu lệnh cho bot
    set_bot_commands()
    
    # Chạy thread kiểm tra cảnh báo
    threading.Thread(target=alert_worker, daemon=True).start()
    
    print("🤖 Bot đang chạy...")
    print("✅ Hỗ trợ nhiều người dùng")
    print("✅ Menu nút bấm bên dưới")
    print("✅ Hiển thị 5 số thập phân")
    
    last_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={'offset': last_id + 1, 'timeout': 30}, timeout=35)
            
            for update in r.json().get('result', []):
                chat_id = None
                
                # Xử lý tin nhắn text
                if 'message' in update and 'text' in update['message']:
                    chat_id = update['message']['chat']['id']
                    text = update['message']['text']
                    process_command(chat_id, text)
                
                # Xử lý callback từ inline keyboard
                elif 'callback_query' in update:
                    chat_id = update['callback_query']['message']['chat']['id']
                    data = update['callback_query']['data']
                    process_callback(chat_id, data)
                    
                    # Trả lời callback
                    callback_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                    requests.post(callback_url, json={'callback_query_id': update['callback_query']['id']})
                
                if update.get('update_id', 0) > last_id:
                    last_id = update['update_id']
                    
        except Exception as e:
            print(f"Lỗi: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
