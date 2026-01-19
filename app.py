import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import os

# --- 1. アイコン・ページ設定 (記述維持) ---
# icon.png があれば使い、なければ青いハートにします
icon_path = "icon.png"
if os.path.exists(icon_path):
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=icon_path, layout="wide")
else:
    st.set_page_config(page_title="KOKOROZASHI Blue", page_icon="💙", layout="wide")

# --- 2. データ復元ロジック (URLから読み込み) ---
def get_data_from_url():
    query_params = st.query_params
    if "data" in query_params:
        try:
            # URLからデータを解読
            decoded = urllib.parse.unquote(query_params["data"])
            rows = [r.split(",") for r in decoded.split("|") if r]
            return pd.DataFrame(rows, columns=["Ticker", "AvgPrice", "Shares"])
        except:
            return pd.DataFrame(columns=["Ticker", "AvgPrice", "Shares"])
    return pd.DataFrame([["RKLB", 0.0, 0], ["TSLA", 0.0, 0]], columns=["Ticker", "AvgPrice", "Shares"])

# --- 3. メイン画面レイアウト ---
st.title("🛡️ KOKOROZASHI Blue")

# データの読み込み
if 'df' not in st.session_state:
    st.session_state.df = get_data_from_url()

tab1, tab2 = st.tabs(["📈 Dashboard (表示)", "⚙️ Settings (入力・保存)"])

with tab2:
    st.subheader("1. 保有銘柄の入力")
    # 入力テーブル
    edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
    
    st.subheader("2. 保存の手順")
    st.warning("⚠️ 重要：下のボタンを押して生成された『保存用URL』を、ブラウザのブックマークやiPhoneのホーム画面に登録してください。")
    
    if st.button("保存用URLを発行する"):
        # データを文字列に変換してURLを作成
        data_list = []
        for _, row in edited_df.iterrows():
            if row["Ticker"]:
                data_list.append(f"{row['Ticker']},{row['AvgPrice']},{row['Shares']}")
        
        data_str = "|".join(data_list)
        encoded_data = urllib.parse.quote(data_str)
        
        # 現在のURLを取得してデータパラメータを付与
        save_link = f"/?data={encoded_data}"
        st.query_params["data"] = data_str # ブラウザのURLを書き換える
        
        st.success("✅ URLを更新しました！")
        st.markdown(f"**[このリンクをブックマークしてください]({save_link})**")
        st.info("iPhoneの場合：この状態でSafariの『ホーム画面に追加』をすると、この入力内容が保存された状態で起動します。")

with tab1:
    # 為替取得
    try:
        rate = yf.Ticker("USDJPY=X").history(period="1d")['Close'].iloc[-1]
    except:
        rate = 150.0

    if not edited_df.empty:
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
                    "Profit/Loss": f"{pl:+.2f}",
                    "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                    "Value (JPY)": f"¥{int(mkt_val * rate):,}"
                })
            except:
                continue

        # サマリー
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", f"¥{int(total_val * rate):,}")
        c2.metric("Total Profit/Loss", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")

        # 結果テーブル
        if results:
            st.table(pd.DataFrame(results).set_index("Symbol"))
    else:
        st.info("Settingsタブで銘柄を入力してください。")

st.caption(f"USD/JPY: {rate:.2f} | 志 Blue v2.2")
