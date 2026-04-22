import streamlit as st
import requests
from collections import defaultdict

# ======================
# 🌐 基本設定
# ======================
st.set_page_config(page_title="公車即時查詢系統", layout="wide")
st.title("🚌 公車即時查詢系統（Streamlit版）")

# ======================
# 🔑 TDX API
# ======================
CLIENT_ID = "你的CLIENT_ID"
CLIENT_SECRET = "你的CLIENT_SECRET"

auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

token = requests.post(auth_url, data={
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}).json()["access_token"]

headers = {"authorization": f"Bearer {token}"}

# ======================
# 🚌 站牌資料
# ======================
@st.cache_data
def load_stops():
    coord = {}
    stop_uid = {}

    for city in ["Taipei", "NewTaipei"]:
        url = f"https://tdx.transportdata.tw/api/basic/v2/Bus/Stop/City/{city}?$format=JSON"
        data = requests.get(url, headers=headers).json()

        for s in data:
            try:
                name = s["StopName"]["Zh_tw"]
                coord[name] = [
                    s["StopPosition"]["PositionLat"],
                    s["StopPosition"]["PositionLon"]
                ]
                stop_uid[name] = s["StopUID"]
            except:
                pass

    return coord, stop_uid

coord, stop_uid = load_stops()

# ======================
# ⏱ ETA
# ======================
def load_eta():
    eta_map = defaultdict(list)

    for city in ["Taipei", "NewTaipei"]:
        url = f"https://tdx.transportdata.tw/api/advanced/v2/Bus/EstimatedTimeOfArrival/City/{city}?$format=JSON"
        data = requests.get(url, headers=headers).json()

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

    return eta_map

eta_map = load_eta()

# ======================
# 🔍 搜尋功能
# ======================
search = st.text_input("🔍 搜尋站牌（輸入關鍵字）")

selected = None

if search:
    results = [k for k in coord.keys() if search in k][:10]

    st.write("### 搜尋結果")

    for r in results:
        if st.button(r):
            selected = r

# ======================
# 📍 顯示站牌資訊
# ======================
if selected:

    st.subheader(f"📍 {selected}")

    uid = stop_uid.get(selected)

    # ETA
    st.markdown("### ⏱ 即時公車")

    if uid in eta_map and len(eta_map[uid]) > 0:
        for e in eta_map[uid]:
            st.write("🚌", e)
    else:
        st.warning("🚫 無即時資料（TDX未提供或未更新）")

    # 地圖
    st.markdown("### 🗺️ 位置")

    st.map([
        {
            "lat": coord[selected][0],
            "lon": coord[selected][1]
        }
    ])
