import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
from datetime import datetime

# --- 1. ページ設定 (極めてシンプルに) ---
st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        h1 { font-size: 1.5rem !important; color: #1E88E5; }
        .stMetric { background: #f8f9fa; padding: 10px; border-radius: 5px; }
        font-size: 12px !important;
    </style>
    """, unsafe_allow_html=True)

# --- 2. データの復元 (URLから) ---
query_params = st.query_params
url_data = {}
if "data" in query_params:
    try:
        decoded = urllib.parse.unquote(query_params["data"])
        for item in decoded.split("|"):
            p = item.split(",")
            if len(p) >= 3:
                url_data[p[0].upper()] = {"Avg": float(p[1]), "Sh": float(p[2])}
    except: pass

# --- 3. サイドバー (設定) ---
st.sidebar.header("⚙️ Setting")
ticker_input = st.sidebar.text_area("Ticker List (comma separated)", value="RKLB, JOBY, QS, BKSY, PL, ASTS")
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# ポートフォリオ編集
st.sidebar.markdown("---")
st.sidebar.subheader("📝 Edit Portfolio")
init_rows = [{"Ticker": t, "AvgPrice": url_data.get(t,{}).get("Avg",0.0), "Shares": url_data.get(t,{}).get("Sh",0.0)} for t in tickers]
edited_df = st.sidebar.data_editor(pd.DataFrame(init_rows), hide_index=True)

if st.sidebar.button("💾 Save & Refresh"):
    d_list = [f"{r['Ticker']},{r['AvgPrice']},{r['Shares']}" for _, r in edited_df.iterrows() if r["Ticker"]]
    st.query_params["data"] = "|".join(d_list)
    st.rerun()

# --- 4. メイン表示 ---
st.title("KOKOROZASHI Blue")

if not tickers:
    st.info("サイドバーに銘柄を入力してください。")
else:
    results, total_val, total_pl, rate = [], 0.0, 0.0, 150.0

    try:
        # 【最速・最小負荷】全銘柄＋為替を1回のリクエストで取得
        # プレマーケット価格を取得するため interval="1m" を使用
        data = yf.download(tickers + ["USDJPY=X"], period="1d", interval="1m", include_extghours=True, progress=False)
        
        if not data.empty:
            # 為替
            try: rate = data['Close']['USDJPY=X'].dropna().iloc[-1]
            except: rate = 150.0

            # 各銘柄
            for t in tickers:
                try:
                    # 銘柄が1つの場合と複数の場合でデータの構造が変わるのを処理
                    p_series = data['Close'][t].dropna() if len(tickers + ["USDJPY=X"]) > 1 else data['Close'].dropna()
                    if p_series.empty: continue
                    
                    curr = float(p_series.iloc[-1])
                    row = edited_df[edited_df["Ticker"] == t].iloc[0]
                    avg, sh = float(row["AvgPrice"]), float(row["Shares"])
                    
                    m_val = curr * sh
                    pl = m_val - (avg * sh)
                    total_val += m_val
                    total_pl += pl

                    results.append({
                        "Symbol": t, 
                        "Price": f"${curr:.2f}", 
                        "P/L (%)": f"{(pl/(avg*sh)*100):+.1f}%" if (avg*sh)>0 else "0%",
                        "Value (JPY)": f"¥{int(m_val * rate):,}"
                    })
                except: continue
    except Exception as e:
        st.error("Market connection busy. Please wait a moment.")

    # 資産表示
    c1, c2 = st.columns(2)
    c1.metric("Total Assets", f"¥{int(total_val * rate):,}")
    c2.metric("Total P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

    if results:
        st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.warning("データの取得に失敗しました。少し時間を置いて更新してください。")

st.caption(f"USD/JPY: {rate:.2f} | Last Update: {datetime.now().strftime('%H:%M:%S')} | v6.0 (Simple)")
