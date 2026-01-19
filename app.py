import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# --- 1. アイコン・ページ設定 ---
icon_path = "icon.png"
if os.path.exists(icon_path):
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=icon_path, layout="wide")
else:
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="💙", layout="wide")

# RSI計算関数
def get_rsi(ticker):
    try:
        d = yf.Ticker(ticker).history(period="1mo")
        delta = d['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
    except: return 50

# --- 2. データ復元ロジック ---
def get_data_from_url():
    query_params = st.query_params
    if "data" in query_params:
        try:
            decoded = urllib.parse.unquote(query_params["data"])
            rows = [r.split(",") for r in decoded.split("|") if r]
            return pd.DataFrame(rows, columns=["Ticker", "AvgPrice", "Shares"])
        except: pass
    return pd.DataFrame([["RKLB", 0.0, 0]], columns=["Ticker", "AvgPrice", "Shares"])

st.title("🛡️ KOKOROZASHI Blue")

if 'df' not in st.session_state:
    st.session_state.df = get_data_from_url()

tab1, tab2 = st.tabs(["📈 Dashboard", "⚙️ Settings"])

with tab2:
    st.subheader("銘柄・保有情報の編集")
    edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
    
    if st.button("保存用URLを発行する"):
        data_list = [f"{row['Ticker']},{row['AvgPrice']},{row['Shares']}" for _, row in edited_df.iterrows() if row["Ticker"]]
        data_str = "|".join(data_list)
        st.query_params["data"] = data_str
        st.success("✅ URLを更新しました。この状態で『ホーム画面に追加』またはブックマークをしてください。")

with tab1:
    try:
        rate = yf.Ticker("USDJPY=X").history(period="1d")['Close'].iloc[-1]
    except: rate = 150.0

    if not edited_df.empty:
        results = []
        total_val, total_pl = 0, 0
        
        for _, row in edited_df.iterrows():
            ticker = str(row["Ticker"]).upper().strip()
            if not ticker or ticker == "None": continue
            
            try:
                stock = yf.Ticker(ticker)
                curr = stock.history(period="1d")['Close'].iloc[-1]
                avg = float(row["AvgPrice"])
                shares = float(row["Shares"])
                
                # 計算
                mkt_val = curr * shares
                cost = avg * shares
                pl = mkt_val - cost
                total_val += mkt_val
                total_pl += pl
                
                # 指値とシグナル
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
        st.info("Settingsタブで銘柄を入力してください。")

st.caption(f"USD/JPY: {rate:.2f} | 志 Blue v2.3")
