from flask import Flask
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time

# --- CẤU HÌNH ---
app = Flask('')
@app.route('/')
def home(): return "Bot Hunter Pro v3 is Live!"

TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- XỬ LÝ THEO DÕI TIKTOK ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS: return
    
    clean_name = username.replace("@", "")
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã kết nối:</b> @{clean_name}")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        # Lấy dữ liệu rương (Sửa lỗi nhận diện thuộc tính)
        try:
            coins = getattr(event, 'coins', 0)
            people = getattr(event, 'can_win_count', 0)
            wait_time = getattr(event, 'wait_time', "...")
            
            if coins == 0: return # Chống rương ảo

            msg = (f"🎁 <b>CÓ RƯƠNG THẬT!</b>\n\n👤 <b>Kênh:</b> @{clean_name}\n"
                   f"💰 <b>Trị giá:</b> {coins} Xu / {people} người\n⏳ <b>Chờ:</b> {wait_time}s\n"
                   f"🔗 <a href='https://www.tiktok.com/@{clean_name}/live'>VÀO NHẶT NGAY</a>")
            send_tele(msg)
        except: pass

    try:
        await client.start()
    except:
        ACTIVE_CLIENTS.pop(username, None)

# --- QUÉT TIN NHẮN TELEGRAM (Dùng Thread riêng) ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống khởi động lại thành công!</b>")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        cmd = update["message"]["text"].strip()
                        
                        if cmd.startswith("@") or (len(cmd) > 2 and " " not in cmd):
                            target = cmd if cmd.startswith("@") else f"@{cmd}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
                        
                        elif cmd == "/list":
                            names = list(ACTIVE_CLIENTS.keys())
                            send_tele(f"📝 Đang xem {len(names)} kênh:\n" + ("\n".join(names) if names else "Trống"))
        except: pass
        time.sleep(2)

# --- CHẠY ---
if __name__ == '__main__':
    # Tạo loop chạy ngầm
    new_loop = asyncio.new_event_loop()
    def run_loop(l):
        asyncio.set_event_loop(l)
        l.run_forever()

    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    Thread(target=run_loop, args=(new_loop,)).start()
    tele_worker(new_loop)
