import time
from fugle_marketdata import WebSocketClient

# 1. 設定您的富果 API Key
API_KEY = "您的_富果_API_KEY"

# 2. 初始化客戶端
client = WebSocketClient(api_key=API_KEY)

# ─── 事件定義 ───

def on_connect():
    """當成功建立連線時觸發"""
    print("\n🟢 [連線成功] 已成功建立 WebSocket 連線通道！")
    print("👉 正在嘗試訂閱測試商品 (台積電 2330)...")
    
    # 連線成功後，主動訂閱台積電的成交明細 (trades) 來測試資料流
    client.subscribe({
        "channel": "trades",
        "symbol": "2330"
    })

def on_disconnect(code, reason):
    """當連線中斷時觸發"""
    print(f"\n🔴 [連線中斷] 連線已結束。代碼: {code}, 原因: {reason}")

def on_error(exception):
    """當發生錯誤或驗證失敗時觸發"""
    print(f"\n⚠️  [連線異常] 發生錯誤，請檢查 API Key 是否正確。內容: {exception}")

def on_message(message):
    """當成功接收到富果伺服器傳回的資料時觸發"""
    print("\n🔵 [接收資料] 成功收到富果 API 回傳訊息！")
    print(f"📦 資料內容: {message}")
    print("🎉 恭喜！這代表您的連線、驗證、資料訂閱全部正常運作。")

# ─── 註冊檢測事件 ───
client.on("connect", on_connect)
client.on("disconnect", on_disconnect)
client.on("error", on_error)
client.on("message", on_message)

# ─── 執行檢測 ───
if __name__ == "__main__":
    print("🚀 開始執行富果 API WebSocket 連線檢測...")
    try:
        # 開始連線（此為阻塞式連線，會持續監聽）
        client.connect()
    except KeyboardInterrupt:
        print("\n👋 檢測被使用者手動中止。")
        client.disconnect()
