from flask import Flask, request, render_template_string
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent
import requests
import os
import asyncio
import time
import re

# --- CẤU HÌNH HỆ THỐNG CHÍNH ---
# DÁN LINK RENDER CỦA BẠN VÀO ĐÂY (Giữ nguyên dấu ngoặc kép)
WEB_URL = "https://tiktok-bot-live.onrender.com/" 

TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

# --- WEB SERVER (TẠO TRANG ĐẾM NGƯỢC) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Hunter Server is Running!"

@app.route('/timer')
def timer():
    t = request.args.get('t', 0, type=int)
    user = request.args.get('user', 'TikTok')
    coins = request.args.get('c', '0')
    
    # Giao diện web đếm ngược phong cách iPhone
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <title>Đếm ngược Rương</title>
        <style>
            body { background-color: #000; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .info { font-size: 22px; color: #ff2d55; margin-bottom: 5px; font-weight: 500;}
            .coins { font-size: 16px; color: #8e8e93; margin-bottom: 40px;}
            .timer { font-size: 90px; font-weight: 200; font-variant-numeric: tabular-nums; letter-spacing: -2px; }
            .btn { margin-top: 60px; padding: 18px 40px; background-color: #ff2d55; color: white; text-decoration: none; border-radius: 30px; font-size: 18px; font-weight: 600; width: 70%; text-align: center; }
            .btn:active { opacity: 0.7; }
        </style>
    </head>
    <body>
        <div class="info">@{{user}}</div>
        <div class="coins">🎁 Rương: {{coins}} Xu</div>
        <div class="timer" id="time">00:00</div>
        
        <a href="https://www.tiktok.com/@{{user}}/live" class="btn">MỞ TIKTOK NGAY</a>

        <script>
            var target = {{t}} * 1000;
            var x = setInterval(function() {
                var now = new Date().getTime();
                var distance = target - now;
                
                if (distance <= 0) {
                    clearInterval(x);
                    document.getElementById("time").innerHTML = "00:00";
                    document.getElementById("time").style.color = "#32d74b"; // Xanh lá khi hết giờ
                    return;
                }
                
                var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var s = Math.floor((distance % (1000 * 60)) / 1000);
                
                m = (m < 10) ? "0" + m : m;
                s = (s < 10) ? "0" + s : s;
                
                document.getElementById("time").innerHTML = m + ":" + s;
            }, 1000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html, t=t, user=user, coins=coins)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- THEO DÕI TIKTOK ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS: return
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}")

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            raw_data = str(vars(event))
            
            # Quét Xu
            match_coins = re.search(r"string_value='(\d+)'", raw_data)
            coins = match_coins.group(1) if match_coins else "0"
            if coins == "0": return

            # Quét Số người & Thời gian
            match_people = re.search(r"can_win_count[:=]\s*(\d+)", raw_data)
            people = match_people.group(1) if match_people else "..."
            
            match_time = re.search(r"wait_time[:=]\s*(\d+)", raw_data)
            wait_time = int(match_time.group(1)) if match_time else 0

            # Tính toán thời gian mở chính xác trong tương lai
            target_time = int(time.time()) + wait_time
            
            # Tạo đường link trang đếm ngược
            timer_link = f"{WEB_URL}/timer?t={target_time}&user={clean_name}&c={coins}"

            msg = (f"🎁 <b>PHÁT HIỆN RƯƠNG!</b>\n\n"
                   f"👤 <b>Kênh:</b> @{clean_name}\n"
                   f"💰 <b>Trị giá:</b> {coins} Xu / {people} người\n"
                   f"⏱ <b>Mở sau:</b> {wait_time} giây\n\n"
                   f"👉 <a href='{timer_link}'>BẤM VÀO ĐÂY ĐỂ MỞ ĐỒNG HỒ</a>")
            send_tele(msg)
        except: pass

    try: await client.start()
    except: ACTIVE_CLIENTS.pop(username, None)

# --- QUÉT LỆNH TELEGRAM ---
def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống Săn Rương Tốc Độ Cao đã sẵn sàng!</b>\nNhắn tên kênh để bắt đầu.")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        if text == "/list":
                            names = list(ACTIVE_CLIENTS.keys())
                            send_tele(f"📝 Đang xem: " + ", ".join(names) if names else "Trống")
                        elif text.startswith("@") or (len(text) > 2 and " " not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except: time.sleep(2)
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    tiktok_loop = asyncio.new_event_loop()
    Thread(target=lambda: (asyncio.set_event_loop(tiktok_loop), tiktok_loop.run_forever()), daemon=True).start()
    tele_worker(tiktok_loop)
