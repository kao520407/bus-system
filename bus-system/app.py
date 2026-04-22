import requests
import threading
import time
from collections import defaultdict
from IPython.display import HTML
import json

# ======================
# 🔑 API
# ======================
CLIENT_ID = "kaojim123422424-782c33b8-d083-4e86"
CLIENT_SECRET = "d054be22-e8fc-42bf-bcd1-46a69d262899"

auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

token = requests.post(auth_url, data={
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET
}).json()['access_token']

headers = {'authorization': f'Bearer {token}'}

# ======================
# 🚌 站牌資料（台北 + 新北）
# ======================
coord = {}
stop_uid_map = {}

for city in ["Taipei", "NewTaipei"]:
    data = requests.get(
        f"https://tdx.transportdata.tw/api/basic/v2/Bus/Stop/City/{city}?$format=JSON",
        headers=headers
    ).json()

    for s in data:
        try:
            name = s["StopName"]["Zh_tw"]
            lat = s["StopPosition"]["PositionLat"]
            lon = s["StopPosition"]["PositionLon"]
            uid = s.get("StopUID")

            if name and lat and lon and uid:
                coord[name] = [lat, lon]
                stop_uid_map[name] = uid
        except:
            pass

# ======================
# ⏱ ETA（全域資料）
# ======================
eta_map = defaultdict(list)

def load_eta():
    global eta_map
    eta_map = defaultdict(list)

    for city in ["Taipei", "NewTaipei"]:
        try:
            data = requests.get(
                f"https://tdx.transportdata.tw/api/advanced/v2/Bus/EstimatedTimeOfArrival/City/{city}?$format=JSON",
                headers=headers
            ).json()

            for e in data:
                try:
                    uid = e.get("StopUID")
                    route = e["RouteName"]["Zh_tw"]

                    if uid and e.get("EstimateTime") is not None:
                        eta_map[uid].append(
                            f"{route} → {e['EstimateTime']//60} 分鐘"
                        )
                except:
                    pass
        except:
            pass

# 第一次載入
load_eta()

# ======================
# 🔄 每 30 秒更新 ETA（Python背景執行）
# ======================
def auto_refresh():
    while True:
        time.sleep(30)
        load_eta()
        print("⏱ ETA 已更新")

threading.Thread(target=auto_refresh, daemon=True).start()

# ======================
# 🌐 Web UI（Google Maps風格）
# ======================
HTML(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>

<style>
body {{
    margin:0;
    font-family:Arial;
}}

#map {{
    height:100vh;
}}

.panel {{
    position:absolute;
    top:20px;
    left:20px;
    width:340px;
    z-index:999;
    background:white;
    padding:15px;
    border-radius:16px;
    box-shadow:0 10px 25px rgba(0,0,0,0.2);
}}

input {{
    width:100%;
    padding:12px;
    margin:5px 0;
    border-radius:12px;
    border:1px solid #ddd;
    font-size:15px;
}}

.suggest {{
    max-height:180px;
    overflow:auto;
    background:white;
    border-radius:12px;
    border:1px solid #ddd;
    margin-top:5px;
}}

.suggest div {{
    padding:10px;
    cursor:pointer;
}}

.suggest div:hover {{
    background:#e8f0fe;
    color:#1a73e8;
}}

#info {{
    margin-top:10px;
    font-size:14px;
}}
</style>
</head>

<body>

<div class="panel">
<h3>🚌 公車即時系統</h3>

<input id="search" placeholder="搜尋站牌..." oninput="searchStop()">

<div id="suggest" class="suggest"></div>

<div id="info"></div>
</div>

<div id="map"></div>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

<script>

var map = L.map('map').setView([25.04,121.56], 13);

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png')
.addTo(map);

var coord = {json.dumps(coord, ensure_ascii=False)};
var stop_uid_map = {json.dumps(stop_uid_map, ensure_ascii=False)};
var eta_map = {json.dumps(dict(eta_map), ensure_ascii=False)};

var marker = null;
let currentList = [];
window.currentStop = null;

// ======================
// 🔍 搜尋
// ======================
function searchStop() {{
    let v = document.getElementById("search").value;
    let box = document.getElementById("suggest");

    box.innerHTML = "";
    currentList = [];

    if (!v) return;

    for (let k in coord) {{
        if (k.includes(v)) {{
            currentList.push(k);
        }}
    }}

    currentList = currentList.slice(0, 8);

    currentList.forEach(name => {{
        let d = document.createElement("div");
        d.innerHTML = name;
        d.onclick = () => selectStop(name);
        box.appendChild(d);
    }});
}}

// ======================
// 📍 選站
// ======================
function selectStop(name) {{

    window.currentStop = name;

    document.getElementById("search").value = name;
    document.getElementById("suggest").innerHTML = "";

    let p = coord[name];
    if (!p) return;

    if (marker) map.removeLayer(marker);

    marker = L.marker(p).addTo(map);
    map.setView(p, 16);

    showInfo(name);
}}

// ======================
// ⏱ 顯示 ETA
// ======================
function showInfo(name) {{

    let uid = stop_uid_map[name];
    let eta = eta_map[uid];

    let html = "<h4>" + name + "</h4>";

    if (eta && eta.length > 0) {{
        html += "<b>⏱ 即時公車：</b><br>" + eta.join("<br>");
    }} else {{
        html += "🚫 無即時資料（TDX尚未提供）";
    }}

    document.getElementById("info").innerHTML = html;
}}

// ======================
// 🔄 每 5 秒同步 Python 最新 ETA（輕量更新）
 // 👉 注意：用 JSON 方式更新
// ======================
setInterval(() => {{
    eta_map = {json.dumps(dict(eta_map), ensure_ascii=False)};
    if (window.currentStop) {{
        showInfo(window.currentStop);
    }}
}}, 5000);

</script>

</body>
</html>
""")