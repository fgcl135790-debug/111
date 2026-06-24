import streamlit as st

# 設定手機網頁模式
st.set_page_config(page_title="當沖真假希望監控", page_icon="📈", layout="centered")

st.title("📈 當沖「真假希望」監控助手")
st.write("輸入即時盤口數據，秒讀主力真實意圖")

# --- 手機輸入面板 ---
st.subheader("📥 盤中數據輸入")

col1, col2 = st.columns(2)
with col1:
    stock_code = st.text_input("股票代號/名稱", value="2409 友達")
    current_price = st.number_input("當前最新成交價", value=32.5, step=0.05)
    open_price = st.number_input("今日開盤價", value=31.1, step=0.05)
    vwap = st.number_input("當日均價線 (VWAP)", value=31.5, step=0.05)

with col2:
    total_bid_volume = st.number_input("五檔【買方】總掛單量 (張)", value=8000, step=100)
    total_ask_volume = st.number_input("五檔【賣方】總掛單量 (張)", value=18000, step=100)
    tick_type = st.radio("最新大單成交屬性", ["🔴 外盤成交 (紅字搶貨)", "🟢 內盤成交 (綠字砸貨)"])
    tick_volume = st.number_input("該筆大單張數 (張)", value=500, step=10)
    average_tick_volume = st.number_input("該股平時平均每筆張數", value=50, step=5)

# --- 核心運算與判定邏輯 ---
st.markdown("---")
st.subheader("🔮 程式判定結果")

is_big_order = tick_volume >= (average_tick_volume * 3)
tick_type_code = 1 if "🔴" in tick_type else 2

# 初始化號誌燈與訊息
status_color = "gray"
signal_msg = "等待輸入數據..."

if current_price < vwap or current_price < open_price:
    # 狀況一：跌破防線
    if total_bid_volume > (total_ask_volume * 1.5) and tick_type_code == 2 and is_big_order:
        status_color = "red"
        signal_msg = "🚨 絕對的【假希望】！\n\n五檔買盤掛了一堆虛假大單撐盤，但明細全都是內盤大單在瘋狂砸貨。這是最典型的主力假撐盤、真出貨陷阱，快逃！"
    else:
        status_color = "orange"
        signal_msg = "🛑 弱勢觀望：\n\n股價已跌破當日均價線或開盤價，目前由空方主導控盤，絕對不可進場接刀攤平。"
else:
    # 狀況二：在均線之上
    if tick_type_code == 1 and is_big_order:
        if total_ask_volume > (total_bid_volume * 1.3):
            status_color = "green"
            signal_msg = "🔥 這是【真希望】發動！\n\n上方五檔賣單壓頂（假壓盤），但明細出現連續紅色外盤大單強勢吞噬。真主力在不計代價吃貨，順勢做多勝率極高！"
        else:
            status_color = "lightgreen"
            signal_msg = "📈 轉強訊號：\n\n大單持續敲進外盤，股價立足於均價線之上，多方開始試探性進攻。"
    elif total_ask_volume > (total_bid_volume * 1.8) and tick_type_code == 2:
        status_color = "orange"
        signal_msg = "⚠️ 疑似【假希望】（假突破）！\n\n股價雖然在高檔，但上方賣壓異常沉重，且明細開始出現內盤綠字大單偷偷倒貨，提防拉高誘多。"
    else:
        status_color = "blue"
        signal_msg = "⏳ 盤整洗盤中：\n\n股價處於安全區，但目前主力尚未亮牌，請耐心等待爆量突破訊號。"

# --- 手機端視覺燈號輸出 ---
if status_color == "green" or status_color == "lightgreen":
    st.success(signal_msg)
elif status_color == "red":
    st.error(signal_msg)
elif status_color == "orange":
    st.warning(signal_msg)
else:
    st.info(signal_msg)