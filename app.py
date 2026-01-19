import streamlit as st
import yfinance as yf
import pandas as pd

# 7. アプリの設定（アイコンに魚の絵文字を設定）
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="🐟")

# ① 為替（USD/JPY）を自動取得する関数
def get_exchange_rate():
    try:
        ticker = yf.Ticker("USDJPY=X")
        data = ticker.history(period="1d")
        return data['Close'].iloc[-1]
    except:
        return 150.0  # エラー時のバックアップ数値

# サイドバー設定
st.sidebar.title("Settings")

# ⑥ 総予算（Total）と為替（Rate）の英語化
latest_rate = get_exchange_rate()
total_jpy = st.sidebar.number_input("Total Budget (JPY)", value=300000)
rate = st.sidebar.number_input("Exchange Rate (USD/JPY)", value=float(latest_rate), format="%.2f")

# ③ 銘柄を自由に入れ替える機能
# カンマ区切りで入力すると、自動でリスト化されます
default_tickers = "RKLB, JOBY, BROS, TSLA"
tickers_input = st.sidebar.text_area("Tickers (comma separated)", value=default_tickers)
ticker_list = [t.strip().upper() for t in tickers_input.split(",")]

# ② タイトルの簡略化
st.title("KOKOROZASHI Blue")

# 計算処理
results = []
budget_per_stock_usd = (total_jpy / rate) / len(ticker_list)

for ticker in ticker_list:
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        
        # ⑤ 番号を1からにするためのデータ準備
        results.append({
            "Symbol": ticker,
            "Price": f"${price:.2f}",
            "Target (95%)": f"${price * 0.95:.2f}",
            "Budget": f"${budget_per_stock_usd:.2f}",
            "Shares": int(budget_per_stock_usd / price)
        })
    except:
        st.sidebar.error(f"Error: {ticker} not found")

# 結果の表示
if results:
    df = pd.DataFrame(results)
    # ⑤ 左側の数字（インデックス）を1から開始にする
    df.index = range(1, len(df) + 1)
    st.table(df)

# ④ 米国株IPOスケジュールの追加
st.markdown("---")
st.subheader("Upcoming US IPOs")
st.write("最新のIPOスケジュールは以下から確認できます：")
st.link_button("Nasdaq IPO Calendar 🔗", "https://www.nasdaq.com/market-activity/ipos")

# シンプルな英語表示への統一
st.caption("All prices are in USD. Data provided by Yahoo Finance.")
