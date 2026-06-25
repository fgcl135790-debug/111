import streamlit as st
import time
import json
import asyncio
import threading
from fugle_marketdata import WebSocketClient

# --- 📱 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="極速大戶籌碼 (WS版)", page_icon="⚡", layout="centered")
st.markdown("""
    <style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0.5rem; max-width: 100% !important;}
    h1 {font-size: 22px !important; margin-bottom: 5px !important;}
    div[data-testid="stExpander"] {margin-bottom: 0.5rem;}
    hr {margin: 6px 0 !important;}
    p, span, label {font-size: 13px !important;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ 行動大戶籌碼五檔 (零延遲)")

# --- ⚙️ UI 設定區 ---
with st.expander("⚙️ 設定：輸入金鑰 / 更換股票", expanded=False):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        manual_big_order_lots = st.number_input("🔥 大戶定義 (張)", min_value=1, max_value=5000, value=150, step=10)
    with col_u2:
        manual_ratio = st.number_input("📊 參考量比 (倍)", min_value=1.0, max_value=5.0, value=1.2, step=0.1, format="%.1f")

# --- 📦 建立跨執行緒共享記憶體 ---
# Streamlit 每次互動都會重跑程式碼，利用 @st.cache_resource 建立一個不會被洗掉的全域字典
@st.cache_resource
def get_shared_state():
    return {
        'symbol': '',
        'name': '',
        'current_price': 0.0,
        'open_price': 0.0,
        'vwap': 0.0,
        'bids': [],
        'asks': [],
        'last_trade_qty': 0,
        'history': [],
        'hod': 0.0,
        'lod': 9999.0,
        'alerts': [],
        'market_trend': "⚪ 觀望",
        'is_running': False # 控制 WebSocket 是否在執行
    }

state = get_shared_state()

# 如果更換股票，重置狀態
if state['symbol'] != stock_code:
    state['symbol'] = stock_code
    state['current_price'] = 0.0
    state['open_price'] = 0.0
    state['history'] = []
    state['alerts'] = []
    state['is_running'] = False # 強制重連

# --- 🔌 WebSocket 背景執行緒邏輯 ---
def start_websocket_thread(api_key, symbol, big_order_lots):
    async def ws_main():
        client = WebSocketClient(api_key=api_key)
        
        async def handle_message(message):
            try:
                # 1. 解析富果 WS 傳來的 JSON
                msg_data = json.loads(message)
                if 'data' not in msg_data or 'quote' not in msg_data['data']: return
                
                quote = msg_data['data']['quote']
                
                # 2. 更新基礎報價
                current_price = quote.get('lastTrade', {}).get('price', state['current_price'])
                if current_price == 0: return
                
                state['name'] = quote.get('name', f"股票 {symbol}")
                state['current_price'] = current_price
                state['open_price'] = quote.get('priceOpen', current_price) if state['open_price'] == 0 else state['open_price']
                
                # 3. 更新五檔
                state['bids'] = quote.get('bids', [])
                state['asks'] = quote.get('asks', [])
                while len(state['bids']) < 5: state['bids'].append({'price': 0.0, 'size': 0})
                while len(state['asks']) < 5: state['asks'].append({'price': 0.0, 'size': 0})
                
                # 4. 計算 VWAP
                total_vol = quote.get('total', {}).get('tradeVolume', 0)
                total_val = quote.get('total', {}).get('tradeValue', 0)
                state['vwap'] = (total_val / total_vol) if total_vol > 0 else current_price
                
                # 5. HOD / LOD 更新
                if current_price > state['hod'] and state['hod'] != 0:
                    state['alerts'] = [f"🔥 突破今日新高: {current_price:.2f}"]
                if current_price < state['lod'] and state['lod'] != 9999.0:
                    state['alerts'] = [f"🧊 跌破今日新低: {current_price:.2f}"]
                state['hod'] = max(state['hod'], current_price)
                state['lod'] = min(state['lod'], current_price)

                # 6. 大戶明細捕捉邏輯 (零延遲事件觸發)
                last_trade = quote.get('lastTrade', {})
                tick_qty = int(last_trade.get('size', 0))
                tick_price = last_trade.get('price', current_price)
                trade_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
                
                if tick_qty >= big_order_lots and tick_qty != state['last_trade_qty']:
                    state['last_trade_qty'] = tick_qty
                    last_bid = state['bids'][0].get('price', 0.0) if len(state['bids']) > 0 else 0.0
                    last_ask = state['asks'][0].get('price', 0.0) if len(state['asks']) > 0 else 0.0
                    
                    if tick_price >= last_ask and last_ask > 0: side = 'Buy'
                    elif tick_price <= last_bid and last_bid > 0: side = 'Sell'
                    else: side = 'Buy' if tick_price >= state['vwap'] else 'Sell'
                    
                    state['history'].insert(0, {
                        'time': trade_time_str, 'side': side, 'qty': tick_qty, 'price': tick_price
                    })
                    # 保持歷史紀錄在 30 筆內，避免記憶體塞爆
                    state['history'] = state['history'][:30]
                    
            except Exception as e:
                print(f"WS 解析錯誤: {e}")

        # 註冊事件與連線
        client.on('message', handle_message)
        await client.connect()
        # 訂閱個股 Quote
        await client.stock.intraday.quote(symbol=symbol)
        
    # 在背景執行緒中運行 asyncio loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_main())

# --- 🚀 啟動連線防呆機制 ---
if api_key and not state['is_running']:
    state['is_running'] = True
    ws_thread = threading.Thread(
        target=start_websocket_thread, 
        args=(api_key, stock_code, manual_big_order_lots), 
        daemon=True # 主程式關閉時，這條線程自動死亡
    )
    ws_thread.start()

# --- 🎨 UI 畫布容器 ---
alert_spot = st.empty()
price_block = st.empty()
five_ticks_spot = st.empty()
log_spot = st.empty()

if not api_key:
    st.warning("🔑 請先輸入「富果 API Key」連線伺服器。")
    st.stop()

# --- 🔄 UI 高頻渲染迴圈 (0.1秒更新) ---
while True:
    # 渲染警報
    if state['alerts']:
        alert_html = "".join([f"<div style='color:#ffa500; font-size:12px; margin-bottom:2px;'>{a}</div>" for a in state['alerts']])
        alert_spot.markdown(alert_html, unsafe_allow_html=True)

    # 渲染價格區塊
    p_diff = state['current_price'] - state['open_price']
    p_color = "#ff4466" if p_diff >= 0 else "#00ff88"
    tw_time = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
    
    price_block.markdown(
        f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 2px;'>"
        f"<span style='font-size:16px; font-weight:bold;'>📈 {state['name']} ({state['symbol']}) ⚡即時連線中</span>"
        f"<span style='font-size:18px; font-weight:bold; color:{p_color};'>{state['current_price']:.2f}</span>"
        f"</div>"
        f"<div style='font-size:12px; color:#aaa;'>均價線 (VWAP): {state['vwap']:.2f} | 系統時間: {tw_time}</div>", 
        unsafe_allow_html=True
    )

    # 渲染五檔
    if state['bids'] and state['asks']:
        five_ticks_html = "<table style='width:100%; text-align:center; font-size:13px; border-collapse:collapse;'><tr style='background-color:#111; height:22px;'><th style='color:#00ff88;'>買張</th><th style='color:#00ff88;'>買價</th><th style='color:#ff4466;'>賣價</th><th style='color:#ff4466;'>賣張</th></tr>"
        for i in range(5):
            b_p = state['bids'][i].get('price', 0.0) if i < len(state['bids']) else 0.0
            b_v = state['bids'][i].get('size', 0) if i < len(state['bids']) else 0
            a_p = state['asks'][i].get('price', 0.0) if i < len(state['asks']) else 0.0
            a_v = state['asks'][i].get('size', 0) if i < len(state['asks']) else 0
            five_ticks_html += f"<tr style='border-bottom:1px solid #1c1c1c;'><td style='color:#00ff88;'>{b_v if b_v>0 else '-'}</td><td style='color:#00ff88;'>{b_p if b_p>0 else '-'}</td><td style='color:#ff4466;'>{a_p if a_p>0 else '-'}</td><td style='color:#ff4466;'>{a_v if a_v>0 else '-'}</td></tr>"
        five_ticks_html += "</table>"
        five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)

    # 渲染大戶紀錄
    log_html = "<b style='font-size:14px; color:#ddd;'>📜 極速大戶進攻明細</b><hr style='margin:4px 0;'>"
    for item in state['history'][:8]: # 顯示近 8 筆
        color = "#ff4466" if item['side'] == 'Buy' else "#00ff88"
        action = "外盤買進" if item['side'] == 'Buy' else "內盤賣出"
        log_html += f"<div style='color:{color}; font-size:13px;'>{item['time']} | {item['price']} | {item['qty']}張 ({action})</div>"
    log_spot.markdown(log_html, unsafe_allow_html=True)

    # 讓 UI 休息 0.1 秒，避免佔用 100% CPU，這在視覺上等同於「零延遲」
    time.sleep(0.1)
