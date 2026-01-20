import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import requests

# --- 1. アイコン・ページ設定 ---
ICON_URL_LOW = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
ICON_URL_UP = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.PNG"

def get_valid_icon_url():
    try:
        r = requests.head(ICON_URL_LOW, timeout=2)
        return ICON_URL_LOW if r.status_code == 200 else ICON_URL_UP
    except: return ICON_URL_LOW

icon_url = get_valid_icon_url()
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=icon_url, layout="wide")

# CSSによるiPhone最適化
st.markdown(f"""
    <head><link rel="apple-touch-icon" href="{icon_url}"></head>
    <style>
        h1 {{ font-size: 1.4rem !important; margin-bottom: 0; }}
        .stTabs [data-baseweb="tab"] {{ font-size: 13px; padding: 5px; }}
        .stTable {{ font-size: 11px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.1rem !important; }}
    </style>
    """, unsafe_allow_html=True)

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
                parts = item.split(",")
                if len(parts) == 3:
                    t, a, s = parts
                    url_data[t.upper()] = {"AvgPrice": float(a), "Shares": float(s)}
    except: pass

# --- 3. サイドバー ---
st.sidebar.markdown("### 🛡️ KOKOROZASHI")
st.sidebar.link_button("📅 IPO Schedule", "https://www.nasdaq.com/market-activity/ipos")
st.sidebar.markdown("---")
ticker_list_str = st.sidebar.text_area("Ticker List", value="RKLB, JOBY, QS, BKSY, PL, ASTS")
current_tickers = [t.strip().upper() for t in ticker_list_str.split(",") if t.strip()]

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
    st.markdown("### Edit Portfolio")
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True).fillna(0)
    if st.button("Save & Update URL"):
        data_list = [f"{row['Ticker']},{row['AvgPrice']},{row['Shares']}" for _, row in edited_df.iterrows() if row["Ticker"]]
        st.query_params["data"] = "|".join(data_list)
        st.success("Saved!")
        st.rerun()

with tab1:
    try:
        # 為替取得（失敗しても150.0を維持）
        rate_data = yf.download("USDJPY=X", period="1d", progress=False)
        rate = rate_data['Close'].iloc[-1] if not rate_data.empty else 150.0
    except: rate = 150.0

    if not edited_df.empty:
        results = []
        total_val, total_pl = 0.0, 0.0
        
        with st.spinner('Updating prices...'):
            for _, row in edited_df.iterrows():
                t = str(row["Ticker"]).upper().strip()
                if not t: continue
                try:
                    # 5日間分取得して「最新の1件」を確実に拾う
                    # include_extghours=True でプレマーケットもカバー
                    stock_data = yf.download(t, period="5d", interval="1m", include_extghours=True, progress=False)
                    if stock_data.empty:
                        # 1分足がダメなら日足でリトライ
                        stock_data = yf.download(t, period="5d", progress=False)
                    
                    if not stock_data.empty:
                        curr = float(stock_data['Close'].iloc[-1])
                        avg, shares = float(row["AvgPrice"]), float(row["Shares"])
                        mkt_val, cost = curr * shares, avg * shares
                        pl = mkt_val - cost
                        total_val += mkt_val
                        total_pl += pl
                        
                        target_95 = curr * 0.95
                        rsi = get_rsi(t)
                        signal = "🟢 BUY" if rsi < 35 else "🔴 SELL" if rsi > 65 else "⚪️ HOLD"
                        
                        results.append({
                            "Symbol": t, "Price": f"${curr:.2f}", "Target(95%)": f"${target_95:.2f}",
                            "Signal": signal, "P/L ($)": f"{pl:+.2f}", 
                            "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                            "JPY": f"¥{int(mkt_val * rate):,}"
                        })
                except: continue

        c1, c2 = st.columns(2)
        c1.metric("Assets", f"¥{int(total_val * rate):,}")
        c2.metric("P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))
        else:
            st.warning("⚠️ Market data temporarily unavailable. Please refresh or check tickers.")
    else:
        st.info("Set Tickers in sidebar.")

st.caption(f"USD/JPY: {rate:.2f} | v3.4")
