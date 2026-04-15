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
    return "Bot is Active!"

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
        send_tele(f"✅ <b>Đã kết nối thành công:</b> @{clean_name}")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            # Lấy thông số rương linh hoạt theo phiên bản thư viện
            coins = getattr(event, 'coins', 0)
            people = getattr(event, 'can_win_count', 0)
            wait_time = getattr(event, 'wait_time', "...")

            if coins > 0:
                msg = (f"🎁 <b>PHÁT HIỆN RƯƠNG!</b>\n\n"
                       f"👤 <b>Kênh:</b> @{clean_name}\n"
                       f"💰 <b>Trị giá:</b> {coins} Xu / {people} người\n"
                       f"⏳ <b>Chờ:</b> {wait_time}s\n"
                       f"🔗 <a href='https://www.tiktok.com/@{clean_name}/live'>VÀO NHẶT NGAY</a>")
                send_tele(msg)
        except:
            pass

    try:
        await client.start()
    except:
        ACTIVE_CLIENTS.pop(username, None)


# --- QUÉT LỆNH TELEGRAM (Bản sửa lỗi nhận diện nhầm) ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống đã sẵn sàng!</b>\n\n- Nhắn <code>@ten_kenh</code> để săn.\n- Nhắn <code>/list</code> để xem danh sách.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        
                        # Ưu tiên kiểm tra lệnh hệ thống trước
                        if text == "/list":
                            names = list(ACTIVE_CLIENTS.keys())
                            if names:
                                status = "📝 <b>Danh sách đang theo dõi:</b>\n" + "\n".join([f"• {n}" for n in names])
                            else:
                                status = "📝 Hiện tại chưa theo dõi kênh nào."
                            send_tele(status)
                        
                        # Nếu không phải lệnh hệ thống thì mới kiểm tra xem có phải tên kênh không
                        elif text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except:
            time.sleep(2)
        time.sleep(1)


# --- KHỞI CHẠY TỔNG HỢP ---
if __name__ == '__main__':
    # 1. Chạy Flask Web Server ở luồng riêng
    Thread(target=run_flask, daemon=True).start()
    
    # 2. Tạo Event Loop cho TikTok ở luồng riêng
    tiktok_loop = asyncio.new_event_loop()
    def run_tiktok_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    Thread(target=run_tiktok_loop, args=(tiktok_loop,), daemon=True).start()
    
    # 3. Chạy quét Telegram ở luồng chính (giữ bot luôn thức)
    tele_worker(tiktok_loop)

