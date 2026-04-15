from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time

# --- CẤU HÌNH WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Săn Rương (Chế độ TEST) is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CẤU HÌNH CHÍNH ---
TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

# --- THEO DÕI TIKTOK ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS:
        return
    
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã vào phòng Live:</b> @{clean_name}\nĐang trực rương...")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            # Bản test: Bắt mọi thông số có thể, nếu không có thì báo 'Không rõ'
            coins = getattr(event, 'coins', getattr(event, 'treasure_box', {}).get('coins', 'Không rõ'))
            people = getattr(event, 'can_win_count', getattr(event, 'treasure_box', {}).get('can_win_count', 'Không rõ'))
            wait_time = getattr(event, 'wait_time', getattr(event, 'treasure_box', {}).get('time', 'Không rõ'))

            # Bản Test: BÁO MỌI RƯƠNG (Không cần > 0)
            msg = (f"🛠 <b>[TEST] CÓ DỮ LIỆU RƯƠNG!</b>\n\n"
                   f"👤 <b>Kênh:</b> @{clean_name}\n"
                   f"💰 <b>Dữ liệu Xu:</b> {coins}\n"
                   f"👥 <b>Người nhặt:</b> {people}\n"
                   f"⏳ <b>Thời gian:</b> {wait_time}\n"
                   f"🔗 <a href='https://www.tiktok.com/@{clean_name}/live'>VÀO LIVE KIỂM TRA NGAY</a>")
            send_tele(msg)
        except Exception as e:
            send_tele(f"⚠️ <b>[LỖI ĐỌC RƯƠNG]:</b> Không phân tích được rương tại @{clean_name}. Lỗi: {str(e)}")

    try:
        await client.start()
    except Exception as e:
        ACTIVE_CLIENTS.pop(username, None)
        send_tele(f"❌ <b>Mất kết nối với:</b> @{clean_name} (Có thể do kênh đã tắt Live hoặc bị chặn IP)")

# --- QUÉT LỆNH TELEGRAM ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống (BẢN TEST) đã sẵn sàng!</b>\n\n- Nhắn <code>/test</code> để thử tín hiệu báo rương.\n- Nhắn <code>@ten_kenh</code> để bắt đầu săn.\n- Nhắn <code>/list</code> để xem danh sách.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        
                        # Lệnh /test giả lập rương
                        if text == "/test":
                            send_tele("🎁 <b>[GIẢ LẬP] PHÁT HIỆN RƯƠNG!</b>\n\n👤 <b>Kênh:</b> @hethong\n💰 <b>Trị giá:</b> 100 Xu / 50 người\n⏳ <b>Chờ:</b> 180s\n🔗 <b>ĐƯỜNG TRUYỀN TELEGRAM HOẠT ĐỘNG TỐT!</b>")
                            
                        # Lệnh /list
                        elif text == "/list":
                            names = list(ACTIVE_CLIENTS.keys())
                            if names:
                                status = "📝 <b>Danh sách đang theo dõi:</b>\n" + "\n".join([f"• {n}" for n in names])
                            else:
                                status = "📝 Hiện tại chưa theo dõi kênh nào."
                            send_tele(status)
                        
                        # Thêm kênh
                        elif text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except:
            time.sleep(2)
        time.sleep(1)

# --- KHỞI CHẠY TỔNG HỢP ---
if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    
    tiktok_loop = asyncio.new_event_loop()
    def run_tiktok_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    Thread(target=run_tiktok_loop, args=(tiktok_loop,), daemon=True).start()
    
    tele_worker(tiktok_loop)


