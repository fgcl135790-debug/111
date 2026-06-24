import streamlit as st
import time
import requests

# --- 📱 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="美股大戶籌碼監控", page_icon="🇺🇸", layout="centered")

# 使用 CSS 壓縮手機端元件間距，並固定深色底色提高戶外辨識度
st.markdown("""
    <style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0.5rem; max-width: 100% !important;}
    h1 {font-size: 22px !important; margin-bottom: 5px !important;}
    div[data-testid="stExpander"] {margin-bottom: 0.5rem;}
    hr {margin: 6px 0 !important;}
    p, span, label {font-size: 13px !important;}
    </style>
""", unsafe_allow_html=True)

st.title("🇺🇸 美股 Alpaca 大戶籌碼五檔 APP")

with st.expander("⚙️ 設定：輸入美股金鑰 / 更換美股代號 / 模擬測試", expanded=False):
    alpaca_key_id = st.text_input("Alpaca KEY ID (客戶端 ID)", type="password")
    alpaca_secret_key = st.text_input("羊駝秘密鑰匙", type="password")
    stock_code = st.text_input("美股代號 (例如: NVDA、AAPL、TSLA)", value="NVDA").upper()
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        manual_big_order_lots = st.number_input(
            "🔥 大戶定義 (單位：股)", min_value=1, max_value=50000, value=2000, step=500
        )
    with col_u2:
        manual_ratio = st.number_input(
            "📊 參考量比 (倍)", min_value=1.0, max_value=5.0, value=1.2, step=0.1, format="%.1f"
        )
        
    test_mode = st.checkbox("🌙 啟動深夜模擬測試", value=False)

# 📱 乾淨初始化所有容器宣告（100% 絕無殘留任何舊測試網址字串）
retracement_alert_spot = st.empty() 
price_block = st.empty()  
threshold_spot = st.empty()
signal_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>📋 最佳買賣報價 (書頂)</b>", unsafe_allow_html=True)
five_ticks_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>🔥 30秒大戶進攻火網</b>", unsafe_allow_html=True)
history_counter_spot = st.empty()

st.markdown("<b style='font-size:14px; color:#ddd;'>📜 大戶進攻即時紀錄 (30秒內明細)</b>", unsafe_allow_html=True)
log_spot = st.empty()
# --- 🟢 初始化全域狀態機制 ---
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'wave_high_price' not in st.session_state: st.session_state.wave_high_price = 0.0
if 'wave_low_price' not in st.session_state: st.session_state.wave_low_price = 999999.0
if 'wave_alert_text' not in st.session_state: st.session_state.wave_alert_text = None       
if 'wave_alert_expires' not in st.session_state: st.session_state.wave_alert_expires = 0.0  
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None
if 'last_update_time' not in st.session_state: st.session_state.last_update_time = time.time()

if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.wave_high_price = 0.0
    st.session_state.wave_low_price = 999999.0
    st.session_state.wave_alert_text = None
    st.session_state.wave_alert_expires = 0.0
    st.session_state.order_history = []
    st.session_state.last_trade_key = None
    st.session_state.last_stock_code = stock_code
# --- 核心邏輯：美股多空連續性辨識引擎（次數純粹觸發版） ---
def process_market_logic(current_price, big_order_vol, stock_name):
    now_time = time.time()
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')

    if recent_buy_cnt > 0:
        if current_price > st.session_state.wave_high_price: st.session_state.wave_high_price = current_price
    else: st.session_state.wave_high_price = 0.0

    if recent_sell_cnt > 0:
        if current_price < st.session_state.wave_low_price and current_price > 0: st.session_state.wave_low_price = current_price
    else: st.session_state.wave_low_price = 999999.0

    RETRACEMENT = 0.01  
    ALERT_DURATION = 12.0  
    retracement_triggered = False

    if st.session_state.wave_high_price > 0 and recent_buy_cnt >= 3:
        drop_ratio = (st.session_state.wave_high_price - current_price) / st.session_state.wave_high_price
        if drop_ratio >= RETRACEMENT:
            st.session_state.order_history = [x for x in st.session_state.order_history if x['side'] != 'Buy']
            st.session_state.wave_high_price = 0.0
            recent_buy_cnt = 0
            st.session_state.wave_alert_text = f"⚠️ 攻勢中斷：股價自這波攻擊高點 ${st.session_state.wave_high_price} 回撤達 {drop_ratio*100:.2f}%！多頭趨勢破壞，強制清空買盤籌碼。"
            st.session_state.wave_alert_expires = now_time + ALERT_DURATION
            retracement_triggered = True

    if st.session_state.wave_low_price < 999999.0 and recent_sell_cnt >= 3 and not retracement_triggered:
        rebound_ratio = (current_price - st.session_state.wave_low_price) / st.session_state.wave_low_price
        if rebound_ratio >= RETRACEMENT:
            st.session_state.order_history = [x for x in st.session_state.order_history if x['side'] != 'Sell']
            st.session_state.wave_low_price = 999999.0
            recent_sell_cnt = 0
            st.session_state.wave_alert_text = f"💥 空頭止跌：股價自這波低點 ${st.session_state.wave_low_price} 強彈達 {rebound_ratio*100:.2f}%！空方針對性遭到攻破，強制擦除砸貨紀錄。"
            st.session_state.wave_alert_expires = now_time + ALERT_DURATION

    if now_time > st.session_state.wave_alert_expires: st.session_state.wave_alert_text = None  

    counter_html = f"<table style='width:100%; text-align:center; font-size:13px;'><tr><td style='width:49%; background-color:#221215; padding:5px; border-radius:4px;'><span style='color:#ff4466;font-size:11px;'>🔴 30s外盤大單吃貨</span><br><b style='color:#ff4466;font-size:18px;'>{recent_buy_cnt} 次</b></td><td style='width:2%;'></td><td style='width:49%; background-color:#112215; padding:5px; border-radius:4px;'><span style='color:#00ff88;font-size:11px;'>🟢 30s內盤大單倒貨</span><br><b style='color:#00ff88;font-size:18px;'>{recent_sell_cnt} 次</b></td></tr></table>"
    history_counter_spot.markdown(counter_html, unsafe_allow_html=True)

    if st.session_state.order_history:
        log_html = "<div style='background-color:#111; padding:6px; border-radius:4px; font-family:monospace; font-size:12px; max-height:100px; overflow-y:auto; text-align:left; border: 1px solid #222;'>"
        for order in reversed(st.session_state.order_history):
            color = "#ff4466" if order['side'] == 'Buy' else "#00ff88"
            action = "外盤搶吃" if order['side'] == 'Buy' else "內盤砸貨"
            log_html += f"<p style='margin:2px 0; color:{color}; line-height:1.2;'>⏱️ {order['time_str']} | {action} <b style='font-size:12px;'>{order['qty']:,}</b> 股 @ ${order['price']}</p>"
        log_html += "</div>"
        log_spot.markdown(log_html, unsafe_allow_html=True)
    else:
        log_spot.caption("⏳ 30秒內無大戶表態紀錄...")

    if recent_sell_cnt > recent_buy_cnt: decision_text = f"⏳ 偵測中：未出現30秒內連續3筆精確內盤大單 ({big_order_vol}股)，保持觀望..."
    else: decision_text = f"⏳ 偵測中：未出現30秒內連續3筆精確外盤大單 ({big_order_vol}股)，保持觀望..."
        
    if recent_buy_cnt >= 3: decision_text = f"🎯【🔥 做多訊號】{stock_name} 主力突破吃貨，順勢做多！"
    if recent_sell_cnt >= 3: decision_text = f"🎯【💥 做空訊號】{stock_name} 多頭防線潰散，順勢放空！"

    return decision_text, st.session_state.wave_alert_text
# --- API 連線與測試模式控制機制 (🟢 2026 美股免費沙盒字典解耦安全版) ---
if (alpaca_key_id and alpaca_secret_key) or test_mode:
    # 建立正式的 Alpaca REST 連線端點
    api = tradeapi.REST(
        key_id=str(alpaca_key_id).strip(), 
        secret_key=str(alpaca_secret_key).strip(), 
        base_url='https://alpaca.markets', 
        api_version='v2'
    ) if not test_mode else None
    
    @st.fragment(run_every=1.5)
    def start_streaming(code):
        try:
            current_now = time.time()
            elapsed_speed = current_now - st.session_state.last_update_time
            if elapsed_speed > 10.0 or elapsed_speed <= 0: elapsed_speed = 1.50
            st.session_state.last_update_time = current_now

            # =========================================================================
            # 📌 模擬劇本模式
            # =========================================================================
            if test_mode:
                open_price = 120.00
                stock_name = code
                trade_time = int(current_now * 1000)
                cycle = int(current_now) % 40
                
                if cycle < 10:
                    current_price = round(120.05 + (cycle * 0.15), 2)
                    tick_qty = manual_big_order_lots + 500
                    bids_base, asks_base = 5000, int(5000 * manual_ratio * 1.5)
                    tick_price = current_price
                    last_bid, last_ask = round(current_price - 0.10, 2), current_price
                elif cycle < 20:
                    current_price = round(122.50 - ((cycle - 10) * 0.20), 2)
                    tick_qty = 0
                    tick_price = current_price
                    bids_base, asks_base = 4000, 4000
                    last_bid, last_ask = current_price, round(current_price + 0.10, 2)
                elif cycle < 30:
                    current_price = round(119.80 - ((cycle - 20) * 0.20), 2)
                    tick_qty = manual_big_order_lots + 1000
                    bids_base, asks_base = int(5000 * manual_ratio * 1.5), 5000
                    tick_price = round(current_price - 0.10, 2)
                    last_bid, last_ask = round(current_price - 0.10, 2), current_price
                else:
                    current_price = round(117.20 + ((cycle - 30) * 0.20), 2)
                    tick_qty = 0
                    tick_price = current_price
                    bids_base, asks_base = 3000, 3000
                    last_bid, last_ask = round(current_price - 0.10, 2), current_price

                bids = [{'price': round(current_price - 0.10 * i, 2), 'size': bids_base - i * 200} for i in range(1, 6)]
                asks = [{'price': round(current_price + 0.10 * i, 2), 'size': asks_base + i * 100} for i in range(1, 6)]
            # =========================================================================
            # 📌 盤中實時美股 Alpaca 資料串接模式（🟢 網址與代號字典隔離，100% 斬斷錯字物理可能）
            # =========================================================================
            else:
                import requests
                headers = {
                    "X-Alpaca-API-Key-Id": str(alpaca_key_id).strip(), 
                    "X-Alpaca-Secret-Key": str(alpaca_secret_key).strip()
                }
                
                # 🟢 修正：網址字串末尾「絕對沒有變數」，網址乾淨獨立
                url_trade = "https://alpaca.markets"
                url_quote = "https://alpaca.markets"
                
                # 🟢 修正：股票代號完全拆入 params 字典中，Alpaca 網址絕對不可能再跟代號相黏！
                query_params = {
                    "symbols": str(code).strip(),
                    "feed": "iex"
                }
                
                res_trade = requests.get(url_trade, headers=headers, params=query_params).json()
                res_quote = requests.get(url_quote, headers=headers, params=query_params).json()
                
                # 從回傳總列表中，精確撈出這檔個股的專屬 Trade 與 Quote 資料
                trades_dict = res_trade.get('trades', {})
                quotes_dict = res_quote.get('quotes', {})
                
                trade_data = trades_dict.get(code, {})
                quote_data = quotes_dict.get(code, {})
                
                current_price = trade_data.get('p', 0.0)
                open_price = current_price  # 輕量端點以今日首價對齊
                stock_name = code
                
                bid_p = quote_data.get('bp', 0.0) if quote_data.get('bp', 0) > 0 else current_price - 0.01
                bid_v = int(quote_data.get('bs', 5)) * 100  # 還原股數
                ask_p = quote_data.get('ap', 0.0) if quote_data.get('ap', 0) > 0 else current_price + 0.01
                ask_v = int(quote_data.get('as', 5)) * 100
                
                bids = [{'price': round(bid_p - 0.05 * i, 2), 'size': bid_v} for i in range(5)]
                asks = [{'price': round(ask_p + 0.05 * i, 2), 'size': ask_v} for i in range(5)]
                
                tick_qty = int(trade_data.get('s', 0))
                tick_price = current_price
                trade_time = int(time.time() * 1000)
                last_bid = bid_p
                last_ask = ask_p

            # =========================================================================
            # 📌 畫面渲染防線
            # =========================================================================
            if current_price == 0.0 and not test_mode:
                st.warning(f"⏳ 正在連線至美國 Alpaca 伺服器獲取 {code} 即時數據...")
                return
            if st.session_state.open_price == 0.0: st.session_state.open_price = open_price
                
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            if total_bid_vol > 0 and total_ask_vol > 0:
                if total_ask_vol >= total_bid_vol:
                    current_real_ratio = total_ask_vol / total_bid_vol
                    ratio_html = f"量比: <b style='color:#ff4466; font-size:13px;'>{current_real_ratio:.2f} 倍</b> (<span style='color:#ff4466;'>🔴 賣盤壓境：適合突破做多</span>)"
                else:
                    current_real_ratio = total_bid_vol / total_ask_vol
                    ratio_html = f"量比: <b style='color:#00ff88; font-size:13px;'>{current_real_ratio:.2f} 倍</b> (<span style='color:#00ff88;'>🟢 買盤托底：適合主力砸貨做空</span>)"
            else: ratio_html = "量比: 0.00 倍 (⏳ 計算中)"

            mode_prefix = " (🌙美股測試中)" if test_mode else " (🇺🇸美股實時)"
            threshold_spot.markdown(
                f"<div style='font-size:12px; color:#aaa;'>⚙️ 門檻: {manual_big_order_lots} 股 | {ratio_html} | ⚡ {elapsed_speed:.2f} 秒/次{mode_prefix}</div>", 
                unsafe_allow_html=True
            )
            
            five_ticks_html = "<table style='width:100%; text-align:center; font-size:13px; border-collapse:collapse; font-family:monospace;'><tr style='background-color:#111; height:22px;'><th style='color:#00ff88; width:25%; font-size:11px;'>買股</th><th style='color:#00ff88; width:25%; font-size:11px;'>買價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣股</th></tr>"
            for i in range(5):
                five_ticks_html += f"<tr style='height:24px; border-bottom:1px solid #1c1c1c;'><td style='color:#00ff88;'>{bids[i]['size']:,}</td><td style='color:#00ff88; font-weight:bold;'>{bids[i]['price']:.2f}</td><td style='color:#ff4466; font-weight:bold;'>{asks[i]['price']:.2f}</td><td style='color:#ff4466;'>{asks[i]['size']:,}</td></tr>"
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)
            
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= manual_big_order_lots:
                if tick_price >= last_ask: current_side = 'Buy'
                elif tick_price <= last_bid: current_side = 'Sell'
                else: current_side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
                
                tw_tick_time = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
                st.session_state.order_history.append({
                    'timestamp': time.time(), 'time_str': tw_tick_time,
                    'side': current_side, 'qty': tick_qty, 'price': tick_price
                })
                st.session_state.last_trade_key = current_trade_key
            
            p_diff = current_price - st.session_state.open_price
            p_color = "#ff4466" if p_diff >= 0 else "#00ff88"
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            price_block.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 2px;'>"
                f"<span style='font-size:16px; font-weight:bold;'>📈 {stock_name}</span>"
                f"<span style='font-size:18px; font-weight:bold; color:{p_color};'>${current_price:.2f} <span style='font-size:12px;'>({p_diff:+.2f})</span> <span style='color:#888; font-size:11px; font-weight:normal;'>{tw_time_str}</span></span>"
                f"</div>", unsafe_allow_html=True
            )
            
            decision, alert = process_market_logic(current_price, manual_big_order_lots, stock_name)
            if alert: retracement_alert_spot.warning(alert)
            else: retracement_alert_spot.empty()
                
            if "做多" in decision: signal_spot.markdown(f"<div style='background-color:#2e1518; padding:8px; border-radius:4px; border-left:5px solid #ff4466; color:#ff4466; font-size:14px; font-weight:bold;'>{decision}</div>", unsafe_allow_html=True)
            elif "做空" in decision: signal_spot.markdown(f"<div style='background-color:#122618; padding:8px; border-radius:4px; border-left:5px solid #00ff88; color:#00ff88; font-size:14px; font-weight:bold;'>{decision}</div>", unsafe_allow_html=True)
            else: signal_spot.markdown(f"<div style='background-color:#161b22; padding:8px; border-radius:4px; border-left:5px solid #58a6ff; color:#c9d1d9; font-size:13px;'>{decision}</div>", unsafe_allow_html=True)
                
        except Exception as e: st.error(f"美股連線異常: {e}")

    start_streaming(stock_code)
else:
    st.warning("🔑 請先展開上方選單輸入「Alpaca 金鑰」並點開眼睛圖示排除前後空格。")
