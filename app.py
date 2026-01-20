import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
from datetime import datetime

# --- 1. ページ設定 ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

# iPhone用スタイル
st.markdown(f"""
    <head><link rel="apple-touch-icon" href="{ICON_URL}"></head>
    <style>
        h1 {{ font-size: 1.2rem !important; margin-bottom: 0; }}
        .stTable {{ font-size: 11px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.0rem !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ復元 ---
query_params = st.query_params
url_data = {}
if "data" in query_params:
    try:
        decoded = urllib.parse.unquote(query_params["data"])
        for item in decoded.split("|"):
            parts = item.split(",")
            if len(parts) == 3:
                url_data[parts[0].upper()] = {"AvgPrice": float(parts[1]), "Shares": float(parts[2])}
    except: pass

# --- 3. サイドバー ---
st.sidebar.markdown("### 🛡️ KOKOROZASHI")
st.sidebar.link_button("📅 IPO Schedule", "https://www.nasdaq.com/market-activity/ipos")
ticker_list_str = st.sidebar.text_area("Ticker List", value="RKLB, JOBY, QS, BKSY, PL, ASTS")
current_tickers = [t.strip().upper() for t in ticker_list_str.split(",") if t.strip()]

init_rows = []
for t in current_tickers:
    d = url_data.get(t, {"AvgPrice": 0.0, "Shares": 0.0})
    init_rows.append({"Ticker": t, "AvgPrice": d["AvgPrice"], "Shares": d["Shares"]})
df_init = pd.DataFrame(init_rows)

# --- 4. メイン画面 ---
st.title("KOKOROZASHI Blue")
tab1, tab2 = st.tabs(["📈 Dash", "📝 Edit"])

# 変数の初期化（これで今回のような赤いエラーを防ぎます）
rate = 150.0 
results = []
total_val = 0.0
total_pl = 0.0

with tab2:
    st.markdown("### Edit Portfolio")
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True).fillna(0)
    if st.button("Save & Update"):
        d_list = [f"{r['Ticker']},{r['AvgPrice']},{r['Shares']}" for _, r in edited_df.iterrows() if r["Ticker"]]
        st.query_params["data"] = "|".join(d_list)
        st.rerun()

with tab1:
    with st.spinner('Loading...'):
        # 1. 為替取得
        try:
            r_data = yf.Ticker("USDJPY=X").history(period="1d")
            if not r_data.empty: rate = r_data['Close'].iloc[-1]
        except: pass

        # 2. 銘柄データ取得
        for _, row in edited_df.iterrows():
            t = str(row["Ticker"]).upper().strip()
            if not t: continue
            try:
                # プレマーケットを含む最新1件のみを取得
                s = yf.Ticker(t)
                h = s.history(period="1d", include_extghours=True)
                
                if h.empty:
                    # 取れない場合は予備手段
                    curr = s.basic_info.get('lastPrice', 0.0)
                else:
                    curr = h['Close'].iloc[-1]
                
                if curr == 0 or pd.isna(curr): continue

                avg, sh = float(row["AvgPrice"]), float(row["Shares"])
                m_val = curr * sh
                pl = m_val - (avg * sh)
                total_val += m_val
                total_pl += pl
                
                # RSI簡易計算
                rsi_h = s.history(period="1mo")
                rsi_v = 50
                if len(rsi_h) > 14:
                    delta = rsi_h['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss
                    rsi_v = 100 - (100 / (1 + rs)).iloc[-1]
                
                sig = "🟢 BUY" if rsi_v < 35 else "🔴 SELL" if rsi_v > 65 else "⚪️ HOLD"
                
                results.append({
                    "Symbol": t, "Price": f"${curr:.2f}", "Target(95%)": f"${curr*0.95:.2f}",
                    "Signal": sig, "P/L($)": f"{pl:+.2f}", "JPY": f"¥{int(m_val * rate):,}"
                })
            except: continue

    # 表示
    c1, c2 = st.columns(2)
    c1.metric("Assets", f"¥{int(total_val * rate):,}")
    c2.metric("P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")
    
    if results:
        st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.warning("Waiting for Market Data... (Please Refresh)")

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v3.7")
