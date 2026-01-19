import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# --- 1. アイコン・ページ設定 ---
icon_url = "https://github.com/Leciel5th/KOKOROZASHI-Blue/raw/main/icon.png"

st.set_page_config(
    page_title="KOKOROZASHI Blue", 
    page_icon=icon_url, 
    layout="wide"
)

# iPhone用アイコン設定（ホーム画面追加時用）
st.markdown(f'<head><link rel="apple-touch-icon" href="{icon_url}"></head>', unsafe_allow_html=True)

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

# --- 2. データ復元・管理ロジック ---
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

st.title("🛡️ KOKOROZASHI Blue")

# --- 3. サイドバー：銘柄の一括登録 ---
st.sidebar.header("⚙️ 銘柄一括登録")
# ご指定の初期銘柄をデフォルトに設定
default_list = "RKLB, JOBY, QS, BKSY, PL, ASTS"
ticker_input = st.sidebar.text_area("Tickerリスト (カンマ区切り)", value=default_list)
current_tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

# 表の初期データ作成
init_rows = []
for t in current_tickers:
    avg = url_data.get(t, {}).get("AvgPrice", 0.0)
    sh = url_data.get(t, {}).get("Shares", 0.0)
    init_rows.append({"Ticker": t, "AvgPrice": avg, "Shares": sh})

df_init = pd.DataFrame(init_rows)

tab1, tab2 = st.tabs(["📈 Dashboard (指値確認)", "📝 Portfolio Edit (入力・保存)"])

with tab2:
    st.subheader("保有状況の編集")
    # ここで単価と株数を入力。Noneは自動的に0扱い
    edited_df = st.data_editor(df_init, use_container_width=True, hide_index=True)
    edited_df = edited_df.fillna(0)

    if st.button("Save & Update URL (保存)"):
        data_list = []
        for _, row in edited_df.iterrows():
            t = str(row["Ticker"]).strip().upper()
            if t:
                data_list.append(f"{t},{row['AvgPrice']},{row['Shares']}")
        
        data_str = "|".join(data_list)
        st.query_params["data"] = data_str
        st.success("✅ データを保存しました！このURLでホーム画面に登録してください。")
        st.rerun()

with tab1:
    try:
        # 最新の為替レート取得
        rate_ticker = yf.Ticker("USDJPY=X").history(period="1d")
        rate = rate_ticker['Close'].iloc[-1] if not rate_ticker.empty else 150.0
    except: rate = 150.0

    if not edited_df.empty:
        results = []
        total_val, total_pl = 0.0, 0.0
        
        with st.spinner('計算中...'):
            for _, row in edited_df.iterrows():
                ticker = str(row["Ticker"]).upper().strip()
                if not ticker: continue
                
                try:
                    avg = float(row["AvgPrice"])
                    shares = float(row["Shares"])
                    
                    stock = yf.Ticker(ticker)
                    curr = stock.history(period="1d")['Close'].iloc[-1]
                    
                    # 各種計算
                    mkt_val = curr * shares
                    cost = avg * shares
                    pl = mkt_val - cost
                    total_val += mkt_val
                    total_pl += pl
                    
                    # 【メイン機能】指値とシグナル
                    target_95 = curr * 0.95
                    rsi = get_rsi(ticker)
                    signal = "🟢 BUY" if rsi < 35 else "🔴 SELL" if rsi > 65 else "⚪️ HOLD"
                    
                    results.append({
                        "Symbol": ticker,
                        "Price": f"${curr:.2f}",
                        "Target (95%)": f"${target_95:.2f}", # 指値復活
                        "Signal": signal,
                        "P/L ($)": f"{pl:+.2f}",
                        "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                        "Value (JPY)": f"¥{int(mkt_val * rate):,}"
                    })
                except: continue

        # サマリー表示
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", f"¥{int(total_val * rate):,}")
        c2.metric("Total Profit/Loss", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        # メインテーブルの表示
        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.info("サイドバーで銘柄リストを入力してください。")

st.caption(f"USD/JPY: {rate:.2f} | 志 Blue v2.9 (Target Restored)")
