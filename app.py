import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# --- 1. アイコン・ページ設定 (Raw URLへ変換済) ---
# GitHubのURLを直接読み込める形式に変換しています
icon_url = "https://github.com/Leciel5th/KOKOROZASHI-Blue/raw/main/icon.png"

st.set_page_config(
    page_title="KOKOROZASHI Blue", 
    page_icon=icon_url, 
    layout="wide"
)

# RSI計算関数
def get_rsi(ticker):
    try:
        d = yf.Ticker(ticker).history(period="1mo")
        if len(d) < 15: return 50
        delta = d['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
    except: return 50

# --- 2. データ復元・セッション管理 ---
if "df" not in st.session_state:
    query_params = st.query_params
    if "data" in query_params:
        try:
            decoded = urllib.parse.unquote(query_params["data"])
            rows = [r.split(",") for r in decoded.split("|") if r]
            st.session_state.df = pd.DataFrame(rows, columns=["Ticker", "AvgPrice", "Shares"])
        except:
            st.session_state.df = pd.DataFrame([["RKLB", 0.0, 0]], columns=["Ticker", "AvgPrice", "Shares"])
    else:
        st.session_state.df = pd.DataFrame([["RKLB", 10.0, 100]], columns=["Ticker", "AvgPrice", "Shares"])

st.title("🛡️ KOKOROZASHI Blue")

tab1, tab2 = st.tabs(["📈 Dashboard", "⚙️ Settings"])

with tab2:
    st.subheader("Edit Portfolio")
    # data_editor の変更を直接反映
    edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
    st.session_state.df = edited_df

    if st.button("Save & Update URL"):
        valid_df = edited_df.dropna(subset=["Ticker"])
        data_list = []
        for _, row in valid_df.iterrows():
            t = str(row["Ticker"]).strip().upper()
            if t and t != "NONE" and t != "NAN":
                p = row["AvgPrice"] if pd.notnull(row["AvgPrice"]) else 0
                s = row["Shares"] if pd.notnull(row["Shares"]) else 0
                data_list.append(f"{t},{p},{s}")
        
        data_str = "|".join(data_list)
        # URLパラメータを更新してリロード
        st.query_params["data"] = data_str
        st.success("✅ URL Updated! Please check the address bar and Add to Home Screen.")
        st.rerun()  # これによりURLバーが確実に書き換わります

with tab1:
    try:
        rate_ticker = yf.Ticker("USDJPY=X").history(period="1d")
        rate = rate_ticker['Close'].iloc[-1] if not rate_ticker.empty else 150.0
    except: rate = 150.0

    display_df = st.session_state.df

    if not display_df.empty:
        results = []
        total_val, total_pl = 0.0, 0.0
        
        with st.spinner('Calculating...'):
            for _, row in display_df.iterrows():
                ticker = str(row.get("Ticker", "")).upper().strip()
                if not ticker or ticker == "NONE" or ticker == "NAN": continue
                
                try:
                    avg = float(row.get("AvgPrice", 0)) if row.get("AvgPrice") else 0.0
                    shares = float(row.get("Shares", 0)) if row.get("Shares") else 0.0
                    
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="1d")
                    if hist.empty: continue
                    
                    curr = hist['Close'].iloc[-1]
                    mkt_val = curr * shares
                    cost = avg * shares
                    pl = mkt_val - cost
                    total_val += mkt_val
                    total_pl += pl
                    
                    target_95 = curr * 0.95
                    rsi = get_rsi(ticker)
                    signal = "🟢 BUY" if rsi < 35 else "🔴 SELL" if rsi > 65 else "⚪️ HOLD"
                    
                    results.append({
                        "Symbol": ticker,
                        "Price": f"${curr:.2f}",
                        "Target(95%)": f"${target_95:.2f}",
                        "Signal": signal,
                        "P/L ($)": f"{pl:+.2f}",
                        "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                        "Value (JPY)": f"¥{int(mkt_val * rate):,}"
                    })
                except: continue

        # サマリー
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", f"¥{int(total_val * rate):,}")
        c2.metric("Total Profit/Loss", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.info("Please add stocks in the Settings tab.")

st.caption(f"USD/JPY: {rate:.2f} | 志 Blue v2.6")
