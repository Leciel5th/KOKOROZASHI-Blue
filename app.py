import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# --- 1. アイコン・ページ設定 (iPhone完全対応版) ---
# GitHubのRaw URL（直接画像データにアクセスするURL）
icon_url = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"

st.set_page_config(
    page_title="KOKOROZASHI Blue", 
    page_icon=icon_url, 
    layout="wide"
)

# iPhone用：タイトルやヘッダーを小さくし、アイコンを強制認識させる設定
st.markdown(f"""
    <head>
        <link rel="apple-touch-icon" href="{icon_url}">
        <link rel="icon" href="{icon_url}">
    </head>
    <style>
        /* タイトルとヘッダーのサイズをiPhone向けに縮小 */
        h1 {{ font-size: 1.5rem !important; padding-bottom: 0px; }}
        h3 {{ font-size: 1.1rem !important; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
        .stTabs [data-baseweb="tab"] {{ font-size: 14px; padding: 10px; }}
        /* テーブルのフォントサイズ調整 */
        .stTable {{ font-size: 12px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.2rem !important; }}
    </style>
    """, unsafe_allow_html=True)

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

# --- 2. データ管理ロジック ---
query_params = st.query_params
url_data = {}
if "data" in query_params:
    try:
        decoded = urllib.parse.unquote(query_params["data"])
        for item in decoded.split("|"):
            if "," in item:
                t, a, s = item.split(",")
                url_data[t] = {"AvgPrice": float(a), "Shares": float(s)}
    except: pass

# --- 3. サイドバー設定 ---
st.sidebar.markdown(f"### 🛡️ KOKOROZASHI")
# ① IPOスケジュールの復活
st.sidebar.link_button("📅 Nasdaq IPO Calendar", "https://www.nasdaq.com/market-activity/ipos")
st.sidebar.markdown("---")

st.sidebar.header("⚙️ Ticker List")
default_list = "RKLB, JOBY, QS, BKSY, PL, ASTS"
ticker_input = st.sidebar.text_area("Separate with commas", value=default_list)
current_tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

init_rows = []
for t in current_tickers:
    avg = url_data.get(t, {}).get("AvgPrice", 0.0)
    sh = url_data.get(t, {}).get("Shares", 0.0)
    init_rows.append({"Ticker": t, "AvgPrice": avg, "Shares": sh})
df_init = pd.DataFrame(init_rows)

# --- 4. メイン画面 ---
st.title("KOKOROZASHI Blue")

tab1, tab2 = st.tabs(["📈 Dash", "📝 Edit"])

with tab2:
    # ③ シンプルな英語表記に変更
    st.markdown("### Edit Portfolio")
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True)
    edited_df = edited_df.fillna(0)

    if st.button("Save & Update"):
        data_list = [f"{row['Ticker']},{row['AvgPrice']},{row['Shares']}" for _, row in edited_df.iterrows() if row["Ticker"]]
        st.query_params["data"] = "|".join(data_list)
        st.success("Updated! Add to Home Screen.")
        st.rerun()

with tab1:
    try:
        rate = yf.Ticker("USDJPY=X").history(period="1d")['Close'].iloc[-1]
    except: rate = 150.0

    if not edited_df.empty:
        results = []
        total_val, total_pl = 0.0, 0.0
        
        with st.spinner('Loading...'):
            for _, row in edited_df.iterrows():
                ticker = str(row["Ticker"]).upper().strip()
                if not ticker: continue
                try:
                    avg, shares = float(row["AvgPrice"]), float(row["Shares"])
                    stock = yf.Ticker(ticker)
                    curr = stock.history(period="1d")['Close'].iloc[-1]
                    
                    mkt_val = curr * shares
                    cost = avg * shares
                    pl = mkt_val - cost
                    total_val += mkt_val
                    total_pl += pl
                    
                    # メイン機能：指値
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
                        "JPY Value": f"¥{int(mkt_val * rate):,}"
                    })
                except: continue

        c1, c2 = st.columns(2)
        c1.metric("Assets", f"¥{int(total_val * rate):,}")
        c2.metric("P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))

st.caption(f"USD/JPY: {rate:.2f} | v3.0")
