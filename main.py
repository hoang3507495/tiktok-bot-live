from flask import Flask, request, render_template_string
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent, AbstractEvent
import requests
import os
import asyncio
import time
import re
from datetime import datetime, timedelta

# --- CẤU HÌNH HỆ THỐNG ---
WEB_URL = "https://tiktok-bot-live.onrender.com" 

TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}

NOTIFY_TIME = 45 

app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot Hunter v6.5 (Pro UI) is Running!"

@app.route('/timer')
def timer():
    ts = request.args.get('ts', 0, type=int)
    w = request.args.get('w', 0, type=int)
    user = request.args.get('user', 'TikTok')
    coins = request.args.get('c', '0')
    
    elapsed = int(time.time()) - ts
    remaining = w - elapsed - 2 
    if remaining < 0: remaining = 0

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <title>Đếm ngược Rương</title>
        <style>
            body { background-color: #000; color: #fff; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; overflow: hidden; }
            .info { font-size: 24px; color: #ff2d55; margin-bottom: 5px; font-weight: bold;}
            .coins { font-size: 18px; color: #8e8e93; margin-bottom: 20px;}
            .timer { font-size: 95px; font-weight: 200; font-variant-numeric: tabular-nums; letter-spacing: -2px; line-height: 1; display: flex; align-items: baseline; justify-content: center; width: 100%;}
            .timer .ms { font-size: 60px; color: #a1a1a6; margin-left: 2px;}
            .controls { display: flex; gap: 10px; margin-top: 20px; }
            .ctrl-btn { background-color: #1c1c1e; color: #0a84ff; border: 1px solid #3a3a3c; padding: 10px 15px; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; }
            .btn { margin-top: 40px; padding: 18px 0; background-color: #ff2d55; color: white; text-decoration: none; border-radius: 15px; font-size: 20px; font-weight: 600; width: 85%; text-align: center; }
        </style>
    </head>
    <body>
        <div class="info">@{{user}}</div>
        <div class="coins">🎁 Rương: {{coins}} Xu</div>
        <div class="timer" id="time">00:00<span class="ms">.0</span></div>
        <div class="controls">
            <button class="ctrl-btn" onclick="adjustTime(-60)">-1 Phút</button>
            <button class="ctrl-btn" onclick="adjustTime(60)">+1 Phút</button>
            <button class="ctrl-btn" onclick="adjustTime(120)">+2 Phút</button>
        </div>
        <a href="https://www.tiktok.com/@{{user}}/live" class="btn">MỞ TIKTOK NGAY</a>
        <script>
            var remainingSeconds = {{remaining}};
            var targetTime = Date.now() + remainingSeconds * 1000;
            var timerInterval;
            function adjustTime(seconds) {
                targetTime += seconds * 1000;
                clearInterval(timerInterval);
                document.getElementById("time").style.color = "#fff";
                startTimer();
            }
            function updateDisplay() {
                var now = Date.now();
                var distance = targetTime - now;
                if (distance <= 0) {
                    document.getElementById("time").innerHTML = "00:00<span class='ms'>.0</span>";
                    document.getElementById("time").style.color = "#32d74b";
                    return true;
                }
                var m = Math.floor(distance / 60000);
                var s = Math.floor((distance % 60000) / 1000);
                var ms = Math.floor((distance % 1000) / 100);
                document.getElementById("time").innerHTML = (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s) + "<span class='ms'>." + ms + "</span>";
                return false;
            }
            function startTimer() {
                updateDisplay();
                timerInterval = setInterval(function() { if (updateDisplay()) clearInterval(timerInterval); }, 50);
            }
            startTimer();
        </script>
    </body>
    </html>
    """
    return render_template_string(html, remaining=remaining, user=user, coins=coins)

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

# --- LOGIC QUÉT ---
async def start_tracking(username, loop):
    if username in ACTIVE_CLIENTS: return
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client
    
    # Biến lưu trữ người xem
    client.last_viewer_count = "..."

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}")

    # Cập nhật mắt xem liên tục
    @client.on(AbstractEvent)
    async def on_any_event(event: AbstractEvent):
        if hasattr(event, 'viewer_count'):
            client.last_viewer_count = event.viewer_count

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        try:
            raw_data = str(vars(event))
            
            # 1. Nhận diện Xu
            match_coins = re.search(r"string_value='(\d+)'", raw_data)
            coins = match_coins.group(1) if match_coins else "0"
            if coins == "0":
                alt_coins = re.search(r"['\"]?(?:coin|score|diamond_count)['\"]?[:=]\s*(\d+)", raw_data, re.I)
                coins = alt_coins.group(1) if alt_coins else "0"
            if coins == "0": return

            # 2. Nhận diện Số người & Quốc gia (Cờ)
            match_people = re.search(r"(?:can_win_count|winner_count|winner_num|people_count)[:=]\s*(\d+)", raw_data, re.I)
            people = match_people.group(1) if match_people else "1"

            flag = "🏳️" # Mặc định nếu không thấy
            m_region = re.search(r"['\"]?(?:region|country|country_code)['\"]?[:=]\s*['\"]([a-zA-Z]{2})['\"]", raw_data, re.I)
            if m_region:
                c_code = m_region.group(1).upper()
                flag = chr(ord(c_code[0]) + 127397) + chr(ord(c_code[1]) + 127397)

            # 3. Giải mã thời gian (Timestamp Decoder)
            wait_sec = 0
            current_ms = int(time.time() * 1000)
            all_13_digits = re.findall(r"\b(17\d{11})\b", raw_data)
            for ts_str in all_13_digits:
                diff_sec = (int(ts_str) - current_ms) / 1000
                if 10 < diff_sec <= 600: 
                    wait_sec = int(diff_sec)
                    break 

            if wait_sec == 0:
                m_exact = re.search(r"(?:wait_time|duration)['\"]?[:=]\s*(\d{2,4})\b", raw_data, re.I)
                wait_sec = int(m_exact.group(1)) if m_exact else 300

            event_ts = int(time.time())
            delay_time = wait_sec - NOTIFY_TIME 
            if delay_time > 0:
                await asyncio.sleep(delay_time)

            current_elapsed = int(time.time()) - event_ts
            actual_remaining = wait_sec - current_elapsed
            if actual_remaining < 0: actual_remaining = 0

            if actual_remaining > 0:
                timer_url = f"{WEB_URL}/timer?ts={event_ts}&w={wait_sec}&user={clean_name}&c={coins}"
                room_id = getattr(client, 'room_id', '...')
                viewers = client.last_viewer_count
                
                vn_time = (datetime.utcnow() + timedelta(hours=7)).strftime("%H:%M:%S")

                msg = (f"👤 <b>KÊNH :</b> @{clean_name} ({room_id})\n"
                       f"🎁 <b>RƯƠNG :</b> {coins} /{people} {flag}\n"
                       f"⏱ <b>Mở Sau :</b> {actual_remaining}s - {vn_time}\n"
                       f"👀 <b>:</b> {viewers}\n"
                       f"👉 <a href='{timer_url}'><b>ĐỒNG HỒ ĐẾM NGƯỢC</b></a>\n"
                       f"› tiktok.com/share/live/{room_id}")
                send_tele(msg)
        except: pass

    try: await client.start()
    except: ACTIVE_CLIENTS.pop(username, None)

def tele_worker(loop):
    last_id = 0
    send_tele("🚀 <b>Hệ thống v6.5 Sẵn sàng!</b>\nĐã thêm Mắt xem và Quốc gia rương.")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id + 1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if "result" in r:
                for update in r["result"]:
                    last_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        text = update["message"]["text"].strip()
                        if text.startswith("@") or (len(text) > 2 and " " not in text and "/" not in text):
                            target = text if text.startswith("@") else f"@{text}"
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop), loop)
        except: time.sleep(2)
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    tiktok_loop = asyncio.new_event_loop()
    Thread(target=lambda: (asyncio.set_event_loop(tiktok_loop), tiktok_loop.run_forever()), daemon=True).start()
    tele_worker(tiktok_loop)
