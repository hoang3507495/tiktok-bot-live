from flask import Flask, request, render_template_string
from threading import Thread
from TikTokLive import TikTokLiveClient
from TikTokLive.events import EnvelopeEvent, ConnectEvent, RoomUserSeqEvent
import requests
import os
import asyncio
import time
import re

# --- CẤU HÌNH HỆ THỐNG ---
WEB_URL = "https://tiktok-bot-live.onrender.com" 
TELEGRAM_TOKEN = "8701996946:AAHcxrWvB7C1t1QURjS1k4ibKxDUuNfJzuw"
TELEGRAM_CHAT_ID = "1882718625"
ACTIVE_CLIENTS = {}
ROOM_VIEWERS = {}

PROCESSED_ENVELOPES = []

app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot Hunter v6.4 (Client-Side Sync) is Running!"

@app.route('/timer')
def timer():
    # Bản mới: Nhận trực tiếp mốc thời gian tuyệt đối (target_ts) từ TikTok
    target_ts = request.args.get('target', 0, type=int)
    user = request.args.get('user', 'TikTok')
    coins = request.args.get('c', '...')

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
            // Bỏ qua server Render, dùng thẳng đồng hồ điện thoại của bạn (Date.now())
            var targetTime = {{target_ts}} * 1000;
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
    return render_template_string(html, target_ts=target_ts, user=user, coins=coins)

def send_tele(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

async def start_tracking(username, loop, force_time=0):
    if username in ACTIVE_CLIENTS: return
    clean_name = username.replace("@", "").strip()
    client = TikTokLiveClient(unique_id=clean_name)
    ACTIVE_CLIENTS[username] = client
    ROOM_VIEWERS[username] = "Đang tải..."

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        mode_text = f"Ép đếm {force_time}s" if force_time > 0 else "Đồng bộ Client-Side"
        send_tele(f"✅ <b>Đã vào phòng:</b> @{clean_name}\nChế độ: {mode_text}")

    @client.on(RoomUserSeqEvent)
    async def on_user_seq(event: RoomUserSeqEvent):
        ROOM_VIEWERS[username] = event.viewer_count

    @client.on(EnvelopeEvent)
    async def on_envelope(event: EnvelopeEvent):
        global PROCESSED_ENVELOPES
        raw_data = str(vars(event))
        
        try:
            if "ENVELOPE_DISPLAY_HIDE" in raw_data: return

            match_env_id = re.search(r"envelope_id\s*[:=]\s*['\"]?(\d+)['\"]?", raw_data)
            env_id = match_env_id.group(1) if match_env_id else None

            if env_id and env_id in PROCESSED_ENVELOPES: return

            match_coins = re.search(r"diamond_count[:=]\s*(\d+)", raw_data, re.I)
            coins = match_coins.group(1) if match_coins else "?"
            if coins == "?":
                alt_coins = re.search(r"['\"]?(?:coin|score|string_value)['\"]?[:=]\s*['\"]?(\d+)['\"]?", raw_data, re.I)
                coins = alt_coins.group(1) if alt_coins else "?"

            if coins == "?" or coins == "0": return

            match_people = re.search(r"(?:people_count|can_win_count|winner_count)[:=]\s*(\d+)", raw_data, re.I)
            people = match_people.group(1) if match_people else "?"

            # --- THUẬT TOÁN TÌM MỐC THỜI GIAN TUYỆT ĐỐI (TARGET_TS) ---
            target_ts = 0
            if force_time > 0:
                target_ts = int(time.time()) + force_time
            else:
                match_unpack = re.search(r"unpack_at[:=]\s*['\"]?(\d{10,13})\b", raw_data)
                if match_unpack:
                    unpack_val = int(match_unpack.group(1))
                    target_ts = unpack_val if unpack_val < 10000000000 else int(unpack_val / 1000)

                if target_ts == 0:
                    current_ms = int(time.time() * 1000)
                    all_13_digits = re.findall(r"\b(17\d{11})\b", raw_data)
                    for ts_str in all_13_digits:
                        # Tìm thời gian mở trong khoảng từ 10s đến 10 phút tính từ hiện tại
                        if 10000 < (int(ts_str) - current_ms) <= 600000: 
                            target_ts = int(int(ts_str) / 1000)
                            break 

                if target_ts == 0: 
                    target_ts = int(time.time()) + 180 

            # Tính toán thời gian còn lại (chỉ để hiển thị trên tin nhắn Tele)
            actual_remaining = target_ts - int(time.time())
            if actual_remaining < 0: actual_remaining = 0

            if actual_remaining > 0:
                if env_id:
                    PROCESSED_ENVELOPES.append(env_id)
                    if len(PROCESSED_ENVELOPES) > 50: PROCESSED_ENVELOPES.pop(0)

                current_viewers = ROOM_VIEWERS.get(username, "Không rõ")

                # TRUYỀN THẲNG TARGET_TS VÀO URL
                timer_url = f"{WEB_URL}/timer?target={target_ts}&user={clean_name}&c={coins}"
                msg = (f"🔥 <b>PHÁT HIỆN RƯƠNG!</b>\n\n"
                       f"👤 <b>Kênh:</b> @{clean_name}\n"
                       f"💰 <b>Trị giá:</b> {coins} Xu / {people} người\n"
                       f"👁 <b>Đang xem:</b> {current_viewers} người\n"
                       f"⏱ <b>Mở sau:</b> ~{actual_remaining} giây\n\n"
                       f"👉 <a href='{timer_url}'><b>BẤM MỞ ĐỒNG HỒ & CHUẨN BỊ LỤM</b></a>")
                send_tele(msg)
        except: pass

    try: await client.start()
    except: ACTIVE_CLIENTS.pop(username, None)

def tele_worker(loop):
    last_id = 0
    try: requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset=-1")
    except: pass
    send_tele(f"🚀 <b>Hệ thống v6.4 Sẵn sàng!</b>\nĐã khắc phục lỗi lệch 30s do máy chủ Render trễ mạng.")
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
                        elif text.startswith("@") or (len(text) > 2 and " " not in text and "/" not in text):
                            parts = text.split()
                            target = parts[0]
                            if not target.startswith("@"): target = f"@{target}"
                            
                            force_time = 0
                            if len(parts) > 1 and parts[1].isdigit():
                                force_time = int(parts[1]) * 60 
                            
                            send_tele(f"⏳ Đang kết nối tới {target}...")
                            asyncio.run_coroutine_threadsafe(start_tracking(target, loop, force_time), loop)
        except: time.sleep(1)

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    tiktok_loop = asyncio.new_event_loop()
    Thread(target=lambda: (asyncio.set_event_loop(tiktok_loop), tiktok_loop.run_forever()), daemon=True).start()
    tele_worker(tiktok_loop)

