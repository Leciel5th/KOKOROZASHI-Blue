import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.parse
import requests
from datetime import datetime

# --- 1. アイコン・ページ設定 ---
ICON_URL = "https://raw.githubusercontent.com/Leciel5th/KOKOROZASHI-Blue/main/icon.png"

st.set_page_config(page_title="KOKOROZASHI Blue", page_icon=ICON_URL, layout="wide")

st.markdown(f"""
    <head><link rel="apple-touch-icon" href="{ICON_URL}"></head>
    <style>
        h1 {{ font-size: 1.2rem !important; margin: 0; }}
        .stTabs [data-baseweb="tab"] {{ font-size: 12px; padding: 5px; }}
        .stTable {{ font-size: 10px !important; }}
        div[data-testid="stMetricValue"] {{ font-size: 1.0rem !important; }}
        .stTable td, .stTable th {{ padding: 3px !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ復元 ---
query_params = st.query_params
url_data = {}
if "data" in query_params:
    try:
        decoded = urllib.parse.unquote(query_params["data"])
        for item in decoded.split("|"):
            if "," in item:
                p = item.split(",")
                url_data[p[0].upper()] = {"AvgPrice": float(p[1]), "Shares": float(p[2])}
    except: pass

# --- 3. サイドバー ---
st.sidebar.markdown("### 🛡️ KOKOROZASHI")
st.sidebar.link_button("📅 IPO Schedule", "https://www.nasdaq.com/market-activity/ipos")
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
    if not current_tickers:
        st.info("Set Tickers in sidebar.")
    else:
        with st.spinner('Fetching Batch Data...'):
            try:
                # 1. 為替と全銘柄を「一括」でダウンロード (これが一番速くて確実)
                all_tickers = current_tickers + ["USDJPY=X"]
                # プレマーケットを含む直近データを一括取得
                data = yf.download(all_tickers, period="5d", interval="1m", include_extghours=True, progress=False)
                
                # 2. 為替の抽出
                try:
                    rate = data['Close']['USDJPY=X'].dropna().iloc[-1]
                except: rate = 150.0

                # 3. 各銘柄の計算
                results = []
                total_val, total_pl = 0.0, 0.0
                
                # RSI計算用の1ヶ月データも別途一括で取得 (高速化)
                rsi_data = yf.download(current_tickers, period="1mo", progress=False)['Close']

                for t in current_tickers:
                    try:
                        # 最新価格の取得
                        if len(current_tickers) > 1:
                            prices = data['Close'][t].dropna()
                        else:
                            prices = data['Close'].dropna() # 1銘柄のみの場合
                        
                        if prices.empty: continue
                        curr = float(prices.iloc[-1])
                        
                        # 保有情報の取得
                        row = edited_df[edited_df["Ticker"] == t].iloc[0]
                        avg, shares = float(row["AvgPrice"]), float(row["Shares"])
                        
                        mkt_val = curr * shares
                        cost = avg * shares
                        pl = mkt_val - cost
                        total_val += mkt_val
                        total_pl += pl
                        
                        # RSI計算
                        if len(current_tickers) > 1:
                            s_rsi = rsi_data[t].dropna()
                        else:
                            s_rsi = rsi_data.dropna()

                        delta = s_rsi.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        signal = "🟢 BUY" if rsi_val < 35 else "🔴 SELL" if rsi_val > 65 else "⚪️ HOLD"
                        
                        results.append({
                            "Symbol": t, "Price": f"${curr:.2f}", "Target(95%)": f"${curr*0.95:.2f}",
                            "Signal": signal, "P/L ($)": f"{pl:+.2f}", 
                            "P/L (%)": f"{(pl/cost*100):+.1f}%" if cost > 0 else "0%",
                            "JPY": f"¥{int(mkt_val * rate):,}"
                        })
                    except: continue

                # 表示
                c1, c2 = st.columns(2)
                c1.metric("Assets", f"¥{int(total_val * rate):,}")
                c2.metric("P/L", f"¥{int(total_pl * rate):,}", delta=f"¥{int(total_pl * rate):,}")
                
                if results:
                    st.table(pd.DataFrame(results).set_index("Symbol"))
                else:
                    st.error("Data error. Check if Tickers are correct.")
                    
            except Exception as e:
                st.error(f"Connection Error. Please refresh.")

st.caption(f"USD/JPY: {rate:.2f} | {datetime.now().strftime('%H:%M:%S')} | v3.6")
