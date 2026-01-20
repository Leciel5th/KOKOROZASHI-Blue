import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import yfinance as yf # 為替用

# --- 1. ページ設定 ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
        h1 {{ font-size: 1.2rem !important; margin: 0; }}
        .stTable {{ font-size: 11px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.0rem !important; }}
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
    with st.spinner('Fetching Data...'):
        # 1. 為替取得（これはv4.0で動いていたので維持）
        try:
            rate = yf.Ticker("USDJPY=X").fast_info['lastPrice']
        except: rate = 150.0

        # 2. 株価の一括取得 (yfinanceがダメな時用の軽量版)
        if current_tickers:
            try:
                # 複数の取得方法を組み合わせて「意地でも」取る
                for t in current_tickers:
                    try:
                        ticker = yf.Ticker(t)
                        # fast_infoはブロックされても動く場合が多い
                        curr = ticker.fast_info['lastPrice']
                        
                        # もし値が取れない、または明らかに古い場合は最新の「1分」だけを取得
                        if curr is None or curr == 0:
                            temp_h = ticker.history(period="1d", interval="1m", include_extghours=True)
                            curr = temp_h['Close'].iloc[-1] if not temp_h.empty else 0

                        if curr > 0:
                            row = edited_df[edited_df["Ticker"] == t].iloc[0]
                            avg, sh = float(row["AvgPrice"]), float(row["Shares"])
                            m_val = curr * sh
                            pl = m_val - (avg * sh)
                            total_val += m_val
                            total_pl += pl
                            
                            results.append({
                                "Symbol": t, "Price": f"${curr:.2f}", 
                                "Target(95%)": f"${curr*0.95:.2f}",
                                "P/L($)": f"{pl:+.2f}", "JPY": f"¥{int(m_val * rate):,}"
                            })
                    except: continue
            except:
                st.error("Still blocked. Please wait 5 mins.")

    # 表示
    c1, c2 = st.columns(2)
    c1.metric("Assets", f"¥{int(total_val * rate):,}")
    c2.metric("P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")
    
    if results:
        st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.warning("🔄 Waiting for data... Markets might be extremely busy.")

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v4.1")
