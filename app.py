import streamlit as st
import yfinance as yf
import pandas as pd
import os

# ページ設定
icon_path = "icon.png"
if os.path.exists(icon_path):
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=icon_path, layout="wide")
else:
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="icon.png", layout="wide")

# 為替取得
def get_exchange_rate():
    try:
        data = yf.Ticker("USDJPY=X").history(period="1d")
        return data['Close'].iloc[-1]
    except:
        return 150.0

# RSI（売買シグナル）計算
def get_rsi(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
    except:
        return 50

st.title("🚀 KOKOROZASHI Blue")

# --- サイドバー：基本設定 ---
st.sidebar.header("⚙️ Global Settings")
latest_rate = get_exchange_rate()
rate = st.sidebar.number_input("Exchange Rate (USD/JPY)", value=float(latest_rate))

# --- メイン：ポートフォリオ管理 ---
st.header("📊 Portfolio Management")
tickers_input = st.sidebar.text_area("Monitoring Tickers", value="RKLB, JOBY, BROS, TSLA")
ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

portfolio_data = []

if ticker_list:
    # ユーザー入力用のカラム作成
    cols = st.columns(len(ticker_list))
    
    for i, ticker in enumerate(ticker_list):
        with cols[i]:
            st.subheader(ticker)
            # ① 実績入力機能
            avg_price = st.number_input(f"Avg Price ($)", key=f"p_{ticker}", value=0.0)
            holdings = st.number_input(f"Holdings", key=f"h_{ticker}", value=0)

        # データ取得
        stock = yf.Ticker(ticker)
        curr_price = stock.history(period="1d")['Close'].iloc[-1]
        rsi_val = get_rsi(ticker)
        
        # ② 損益計算
        market_value = curr_price * holdings
        cost_basis = avg_price * holdings
        pl_usd = market_value - cost_basis if holdings > 0 else 0.0
        pl_pct = (pl_usd / cost_basis * 100) if cost_basis > 0 else 0.0
        
        # ③ 売買シグナル判定
        if rsi_val < 35: signal = "🟢 BUY (Oversold)"
        elif rsi_val > 65: signal = "🔴 SELL (Overbought)"
        else: signal = "⚪️ NEUTRAL"

        portfolio_data.append({
            "Ticker": ticker,
            "Price": f"${curr_price:.2f}",
            "RSI": f"{rsi_val:.1f}",
            "Signal": signal,
            "P/L ($)": f"{pl_usd:+.2f}",
            "P/L (%)": f"{pl_pct:+.2f}%",
            "Value (JPY)": f"¥{int(market_value * rate):,}"
        })

    # 結果をテーブル表示
    st.markdown("---")
    df = pd.DataFrame(portfolio_data)
    df.index = range(1, len(df) + 1)
    st.table(df)

# IPOカレンダー
st.sidebar.markdown("---")
st.sidebar.link_button("📅 Nasdaq IPO Calendar", "https://www.nasdaq.com/market-activity/ipos")
st.caption(f"Last updated USD/JPY: {rate:.2f}")
