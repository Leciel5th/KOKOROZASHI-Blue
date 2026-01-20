import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
from datetime import datetime

# --- 1. ページ設定・アイコン ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

# iPhoneで見やすいスリムデザイン
st.markdown(f"""
    <head><link rel="apple-touch-icon" href="{ICON_URL}"></head>
    <style>
        h1 {{ font-size: 1.2rem !important; margin: 0; color: #1E88E5; }}
        .stTabs [data-baseweb="tab"] {{ font-size: 13px; padding: 8px; }}
        .stTable {{ font-size: 11px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.1rem !important; }}
        [data-testid="stMetric"] {{ background: #f0f2f6; padding: 10px; border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ管理ロジック ---
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
st.sidebar.markdown("### 🛡️ KOKOROZASHI v5.0")
ticker_input = st.sidebar.text_area("Ticker List", value="RKLB, JOBY, QS, BKSY, PL, ASTS")
current_tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

init_rows = []
for t in current_tickers:
    d = url_data.get(t, {"AvgPrice": 0.0, "Shares": 0.0})
    init_rows.append({"Ticker": t, "AvgPrice": d["AvgPrice"], "Shares": d["Shares"]})
df_init = pd.DataFrame(init_rows)

# --- 4. メイン画面 ---
st.title("KOKOROZASHI Blue")
tab1, tab2 = st.tabs(["📈 Dash", "📝 Edit"])

rate = 150.0 
results = []
total_val = 0.0
total_pl = 0.0

with tab2:
    st.markdown("### Edit Portfolio")
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True).fillna(0)
    if st.button("Save & Update URL"):
        d_list = [f"{r['Ticker']},{r['AvgPrice']},{r['Shares']}" for _, r in edited_df.iterrows() if r["Ticker"]]
        st.query_params["data"] = "|".join(d_list)
        st.success("Updated! Please switch to Dash tab.")
        st.rerun()

with tab1:
    with st.spinner('Accessing Wall Street...'):
        # 為替取得 (USD/JPY)
        try:
            rate = yf.Ticker("USDJPY=X").fast_info['lastPrice']
        except: rate = 150.0

        for _, row in edited_df.iterrows():
            t = str(row["Ticker"]).upper().strip()
            if not t: continue
            try:
                # 取得を安定させるためにTickerオブジェクトを一度だけ生成
                tk = yf.Ticker(t)
                
                # --- 価格取得（プレマーケット優先） ---
                # 1分足で「市場外取引」を明示的に要求
                h_1d = tk.history(period="1d", interval="1m", include_extghours=True)
                if not h_1d.empty:
                    curr = h_1d['Close'].iloc[-1]
                else:
                    curr = tk.fast_info['lastPrice']
                
                if curr is None or curr <= 0: continue

                # --- 指標計算 (RSI) ---
                sig = "⚪️ HOLD"
                try:
                    h_1mo = tk.history(period="1mo")
                    if len(h_1mo) > 14:
                        delta = h_1mo['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                        rs = gain / loss
                        rsi_v = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        if rsi_v < 35: sig = "🟢 BUY"
                        elif rsi_v > 65: sig = "🔴 SELL"
                except: pass

                # --- 集計 ---
                avg, sh = float(row["AvgPrice"]), float(row["Shares"])
                m_val = curr * sh
                pl = m_val - (avg * sh)
                total_val += m_val
                total_pl += pl
                
                results.append({
                    "Symbol": t, 
                    "Price": f"${curr:.2f}", 
                    "Signal": sig,
                    "P/L (%)": f"{(pl/(avg*sh)*100):+.1f}%" if (avg*sh)>0 else "0%",
                    "P/L ($)": f"{pl:+.2f}",
                    "JPY Value": f"¥{int(m_val * rate):,}"
                })
            except: continue

    # 資産表示
    c1, c2 = st.columns(2)
    c1.metric("Assets", f"¥{int(total_val * rate):,}")
    c2.metric("Total P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")
    
    if results:
        # 表形式で表示
        res_df = pd.DataFrame(results).set_index("Symbol")
        st.table(res_df)
    else:
        st.error("Market connection blocked. Please try again in 5 minutes.")

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v5.0")
