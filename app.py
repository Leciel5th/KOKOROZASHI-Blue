import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# 1. ページ設定
icon_path = "icon.png"
if os.path.exists(icon_path):
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=icon_path, layout="wide")
else:
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="icon.png", layout="wide")

# スタイル調整
st.markdown("<style>table {margin-left: auto; margin-right: auto;}</style>", unsafe_allow_html=True)

# 2. 為替取得（キャッシュして高速化）
@st.cache_data(ttl=3600)
def get_rate():
    try:
        return yf.Ticker("USDJPY=X").history(period="1d")['Close'].iloc[-1]
    except: return 150.0

# 3. URLからデータを読み込む機能
def load_data_from_url():
    params = st.query_params
    if "d" in params:
        try:
            # 形式: Ticker,Avg,Qty|Ticker,Avg,Qty
            raw_data = params["d"]
            rows = [r.split(",") for r in raw_data.split("|")]
            return pd.DataFrame(rows, columns=["Ticker", "AvgPrice", "Shares"])
        except: pass
    return pd.DataFrame(columns=["Ticker", "AvgPrice", "Shares"])

# --- メインロジック ---
st.title("🛡️ KOKOROZASHI Blue")

# データの読み込み
df_portfolio = load_data_from_url()

tab1, tab2 = st.tabs(["📈 Dashboard", "⚙️ Edit & Save"])

with tab2:
    st.subheader("1. 銘柄情報を編集")
    # 編集可能なテーブル
    edited_df = st.data_editor(df_portfolio, num_rows="dynamic", use_container_width=True, key="editor")
    
    st.subheader("2. 保存（iPhoneへ登録）")
    # URLを作成する
    if not edited_df.empty:
        data_str = "|".join([f"{row['Ticker']},{row['AvgPrice']},{row['Shares']}" for _, row in edited_df.iterrows()])
        encoded_data = urllib.parse.quote(data_str)
        save_url = f"https://your-app-url.streamlit.app/?d={encoded_data}" # ここは自分のURLに自動で置き換わります
        
        st.info("下のボタンを押すとURLが更新されます。その後、Safariのメニューから『ホーム画面に追加』をしてください。")
        if st.button("URLを作成して保存準備をする"):
            st.query_params["d"] = data_str
            st.success("URLを更新しました！この状態でホーム画面に追加してください。")

with tab1:
    rate = get_rate()
    if not edited_df.empty and edited_df["Ticker"].notna().any():
        results = []
        total_val, total_pl = 0, 0
        
        for _, row in edited_df.iterrows():
            ticker = str(row["Ticker"]).upper().strip()
            if not ticker or ticker == "NONE": continue
            
            try:
                stock = yf.Ticker(ticker)
                curr = stock.history(period="1d")['Close'].iloc[-1]
                avg = float(row["AvgPrice"])
                shares = float(row["Shares"])
                
                mkt_val = curr * shares
                cost = avg * shares
                pl = mkt_val - cost
                total_val += mkt_val
                total_pl += pl
                
                results.append({
                    "Symbol": ticker,
                    "Price": f"${curr:.2f}",
                    "P/L ($)": f"{pl:+.2f}",
                    "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                    "Value (JPY)": f"¥{int(mkt_val * rate):,}"
                })
            except:
                st.warning(f"Error loading {ticker}")

        # サマリー表示
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", f"¥{int(total_val * rate):,}")
        c2.metric("Total Profit/Loss", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        # 結果テーブル
        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.info("『Edit & Save』タブで銘柄を入力してください。")

st.caption(f"USD/JPY: {rate:.2f} | 志 Blue v2.1 (No-DB Version)")
