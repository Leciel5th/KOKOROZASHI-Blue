import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# --- 1. ページ設定 ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
        h1 {{ font-size: 1.2rem !important; margin: 0; color: #1E88E5; }}
        .stTable {{ font-size: 11px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.0rem !important; }}
        .link-button {{ 
            display: inline-block; padding: 5px 10px; background-color: #f0f2f6; 
            border-radius: 5px; text-decoration: none; color: #1E88E5; font-size: 10px; margin: 2px;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ管理 ---
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

with tab2:
    st.markdown("### Edit Portfolio")
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True).fillna(0)
    if st.button("Save & Update URL"):
        d_list = [f"{r['Ticker']},{r['AvgPrice']},{r['Shares']}" for _, r in edited_df.iterrows() if r["Ticker"]]
        st.query_params["data"] = "|".join(d_list)
        st.rerun()

with tab1:
    results = []
    total_val, total_pl, rate = 0.0, 0.0, 150.0

    with st.spinner('Accessing Real-time Data...'):
        # 1. 為替取得
        try:
            rate = yf.Ticker("USDJPY=X").fast_info['lastPrice']
        except: rate = 150.0

        # 2. 個別銘柄の取得（偽装ヘッダー付き）
        # yfinanceの内部で使うsessionにブラウザを偽装するヘッダーをセット
        import requests_cache
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

        for _, row in edited_df.iterrows():
            t = str(row["Ticker"]).upper().strip()
            if not t: continue
            try:
                tk = yf.Ticker(t, session=session)
                # プレマーケット取得
                h = tk.history(period="1d", interval="1m", include_extghours=True)
                curr = h['Close'].iloc[-1] if not h.empty else tk.fast_info['lastPrice']
                
                if curr is None or curr <= 0: continue

                # RSI計算
                sig, rsi_h = "⚪️ HOLD", tk.history(period="1mo")
                if len(rsi_h) > 14:
                    delta = rsi_h['Close'].diff()
                    gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss
                    rsi_v = 100 - (100 / (1 + rs)).iloc[-1]
                    sig = "🟢 BUY" if rsi_v < 35 else "🔴 SELL" if rsi_v > 65 else "⚪️ HOLD"

                avg, sh = float(row["AvgPrice"]), float(row["Shares"])
                m_val = curr * sh
                pl = m_val - (avg * sh)
                total_val += m_val
                total_pl += pl
                
                results.append({
                    "Symbol": t, "Price": f"${curr:.2f}", "Signal": sig,
                    "P/L (%)": f"{(pl/(avg*sh)*100):+.1f}%" if (avg*sh)>0 else "0%",
                    "P/L ($)": f"{pl:+.2f}", "JPY": f"¥{int(m_val * rate):,}"
                })
            except: continue

    # --- 資産表示 ---
    c1, c2 = st.columns(2)
    c1.metric("Assets", f"¥{int(total_val * rate):,}")
    c2.metric("Total P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

    if results:
        st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        # 万が一遮断された場合、直リンクボタンを表示
        st.error("Connection Blocked by Yahoo. Use Quick Links below:")
        cols = st.columns(3)
        for i, t in enumerate(current_tickers):
            with cols[i % 3]:
                st.markdown(f'<a href="https://finance.yahoo.com/quote/{t}" class="link-button">🔗 {t} Live</a>', unsafe_allow_html=True)

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v5.1")
