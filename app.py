import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
from datetime import datetime

# --- 1. ページ設定 ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <style>
        h1 {{ font-size: 1.2rem !important; margin: 0; color: #1E88E5; }}
        .stTable {{ font-size: 10px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.1rem !important; }}
        .link-button {{ 
            display: inline-block; padding: 4px 8px; background-color: #f0f2f6; 
            border-radius: 5px; text-decoration: none; color: #1E88E5; font-size: 10px; border: 1px solid #ddd;
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
            p = item.split(",")
            if len(p) >= 3:
                url_data[p[0].upper()] = {
                    "Avg": float(p[1]), 
                    "Sh": float(p[2]), 
                    "Manual": float(p[3]) if len(p) > 3 else 0.0
                }
    except: pass

# --- 3. サイドバー ---
st.sidebar.markdown("### 🛡️ KOKOROZASHI v5.4")
ticker_input = st.sidebar.text_area("Ticker List", value="RKLB, JOBY, QS, BKSY, PL, ASTS")
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# --- 4. メイン画面 ---
st.title("KOKOROZASHI Blue")
tab1, tab2 = st.tabs(["📈 Dash", "📝 Edit"])

with tab2:
    st.markdown("##### 📝 Portfolio & Manual Price Override")
    init_rows = []
    for t in tickers:
        d = url_data.get(t, {"Avg": 0.0, "Sh": 0.0, "Manual": 0.0})
        init_rows.append({"Ticker": t, "AvgPrice": d["Avg"], "Shares": d["Sh"], "ManualPrice": d["Manual"]})
    
    edited_df = st.data_editor(pd.DataFrame(init_rows), use_container_width=True, hide_index=True).fillna(0)
    
    if st.button("💾 Save & Update"):
        d_list = [f"{r['Ticker']},{r['AvgPrice']},{r['Shares']},{r['ManualPrice']}" for _, r in edited_df.iterrows() if r["Ticker"]]
        st.query_params["data"] = "|".join(d_list)
        st.success("Saved!")
        st.rerun()

with tab1:
    results, total_val, total_pl, rate = [], 0.0, 0.0, 150.0
    api_success = False

    with st.spinner('Checking Market...'):
        try:
            # 為替と株価の一括取得を試みる
            raw_data = yf.download(tickers + ["USDJPY=X"], period="1d", interval="1m", include_extghours=True, progress=False)
            if not raw_data.empty:
                try: rate = raw_data['Close']['USDJPY=X'].dropna().iloc[-1]
                except: rate = 150.0
                api_success = True
        except:
            api_success = False

    # 銘柄ごとの計算
    for t in tickers:
        try:
            # 1. APIから取得を試みる
            curr = 0.0
            if api_success:
                try:
                    if len(tickers + ["USDJPY=X"]) > 1:
                        curr = float(raw_data['Close'][t].dropna().iloc[-1])
                    else:
                        curr = float(raw_data['Close'].dropna().iloc[-1])
                except: curr = 0.0
            
            # 2. APIがダメ、または手入力がある場合は手入力を優先
            row = edited_df[edited_df["Ticker"] == t].iloc[0]
            if curr <= 0 or row["ManualPrice"] > 0:
                # 手入力があればそれを使う
                if row["ManualPrice"] > 0:
                    curr = float(row["ManualPrice"])
            
            if curr <= 0: continue

            avg, sh = float(row["AvgPrice"]), float(row["Shares"])
            m_val = curr * sh
            pl = m_val - (avg * sh)
            total_val += m_val
            total_pl += pl

            results.append({
                "Symbol": t, "Price": f"${curr:.2f}", 
                "P/L (%)": f"{(pl/(avg*sh)*100):+.1f}%" if (avg*sh)>0 else "0%",
                "JPY Value": f"¥{int(m_val * rate):,}"
            })
        except: continue

    # 資産表示
    c1, c2 = st.columns(2)
    c1.metric("Assets", f"¥{int(total_val * rate):,}")
    c2.metric("Total P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

    if results:
        st.table(pd.DataFrame(results).set_index("Symbol"))
    
    # 接続が Busy な場合や、確認したい場合のためのリンク
    st.markdown("---")
    st.markdown("##### 🔗 Quick Check (Yahoo Finance)")
    cols = st.columns(4)
    for i, t in enumerate(tickers):
        with cols[i % 4]:
            st.markdown(f'<a href="https://finance.yahoo.com/quote/{t}" target="_blank" class="link-button">📈 {t}</a>', unsafe_allow_html=True)

    if not api_success:
        st.info("💡 API is busy. Check 'Live' links above and enter prices in 'Edit' tab to update total assets.")

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v5.4")
