import time
from fugle_marketdata import WebSocketClient, RestClient

# 1. 設定您的富果 API Key (請在此處填入正確的金鑰)
API_KEY = "您的_富果_API_KEY"

# 2. 初始化客戶端
client = WebSocketClient(api_key=API_KEY)
stock = client.stock

# ─── 3. 定義 WebSocket 事件 ───

def on_connect():
    """當成功建立連線時觸發"""
    print("\n🟢 [連線成功] 已成功建立 WebSocket 連線通道！")
    print("👉 正在嘗試訂閱測試商品 (台積電 2330)...")
    
    # 連線成功後，嘗試訂閱台積電的成交明細 (trades)
    stock.subscribe({
        "channel": "trades",
        "symbol": "2330"
    })

def on_disconnect(code, reason):
    """當連線中斷時觸發"""
    print(f"\n🔴 [連線中斷] 連線已結束。代碼: {code}, 原因: {reason}")

def on_error(exception):
    """當發生錯誤或驗證失敗時觸發"""
    print(f"\n⚠️  [連線異常] 事件監聽捕捉到錯誤: {exception}")

def on_message(message):
    """當成功接收到富果伺服器傳回的資料時觸發"""
    print("\n🔵 [接收資料] 成功收到富果 API 回傳訊息！")
    print(f"📦 資料內容: {message}")
    print("🎉 恭喜！這代表您的連線、驗證、資料訂閱全部正常運作。")

# ─── 4. 註冊事件監聽 ───
stock.on("connect", on_connect)
stock.on("disconnect", on_disconnect)
stock.on("error", on_error)
stock.on("message", on_message)

# ─── 5. 額外權限輔助檢查 ───
def check_api_key_via_http():
    """使用 HTTP REST API 交叉驗證 API Key 是否有效"""
    print("\n🔍 正在透過 HTTP 同步驗證 API Key 的可用性...")
    try:
        rest_client = RestClient(api_key=API_KEY)
        # 嘗試撈取台積電基本資料
        rest_client.stock.intraday.ticker(symbol="2330")
        print("✅ HTTP 驗證成功：您的 API Key 在權限與格式上是有效的。")
        return True
    except Exception as e:
        print(f"❌ HTTP 驗證失敗：此 API Key 無法正常讀取資料。")
        print(f"   詳細原因: {e}")
        return False

# ─── 6. 執行主程式 ───
if __name__ == "__main__":
    print("🚀 開始執行富果 API 終極連線檢測程序...")
    
    # 預先做一次 HTTP 檢查，排除 Key 填錯的可能
    is_key_valid = check_api_key_via_http()
    
    print("\n🌐 正在啟動 WebSocket 連線監聽...")
    try:
        # 啟動 WebSocket 連線
        stock.connect()
        
    except KeyboardInterrupt:
        print("\n👋 檢測被使用者手動中止。")
        try:
            stock.disconnect()
        except:
            pass
            
    except Exception as e:
        print("\n❌ [連線失敗] 成功攔截到富果底層拋出的 `raise self.error`！")
        print(f"📋 富果伺服器拒絕的真實原因: {e}")
        print("\n💡 請根據上方原因進行以下排查：")
        print("   1. 原因若為 '401' 或 'Unauthorized' -> 請確認開發者後台的「行情數據 (Market Data)」權限是否開通。")
        print("   2. 原因若包含 'Connection refused' -> 代表您的網路環境（如公司防火牆）封鎖了 WebSocket 443 埠。")
        print("   3. 檢查您的 API Key 前後是否有不小心複製到空格。")
