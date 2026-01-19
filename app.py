import streamlit as st
import yfinance as yf
import pandas as pd

# 1. アプリの設定（タイトルをKOKOROZASHI Blueに変更）
st.set_page_config(page_title="KOKOROZASHI Blue", layout="wide")
st.title("🟦 KOKOROZASHI Blue: 志・投資司令部")

# 2. サイドバー：ユーザー入力エリア
st.sidebar.header("設定")
budget_jpy = st.sidebar.number_input("予算（日本円）", value=300000)
usd_jpy = st.sidebar.number_input("現在の中値（円/ドル）", value=150.0)

# 日本円をドルに換算
budget_usd = budget_jpy / usd_jpy

# 3. 銘柄と配分比率の設定（あなたのポートフォリオ）
portfolio_data = {
    "RKLB": {"ratio": 0.35, "name": "Rocket Lab"},
    "JOBY": {"ratio": 0.25, "name": "Joby Aviation"},
    "ASTS": {"ratio": 0.20, "name": "AST SpaceMobile"},
    "BKSY": {"ratio": 0.10, "name": "BlackSky"},
    "QS": {"ratio": 0.05, "name": "QuantumScape"},
    "PL": {"ratio": 0.05, "name": "Planet Labs"}
}

st.subheader(f"💰 総予算: ${budget_usd:.2f} (約{budget_jpy:,}円)")

# 4. 株価取得と計算
results = []

# 読み込み中の表示
with st.spinner('市場データを取得中...'):
    for symbol, info in portfolio_data.items():
        try:
            ticker = yf.Ticker(symbol)
            # 最新の終値を取得（1日分のデータ）
            history = ticker.history(period="1d")
            
            if not history.empty:
                current_price = history["Close"].iloc[-1]
                
                # 予算配分
                allocated_usd = budget_usd * info["ratio"]
                
                # おすすめ指値（2%引きの価格）
                target_limit = current_price * 0.98
                
                # 購入可能株数
                shares = int(allocated_usd / target_limit)
                
                results.append({
                    "銘柄": symbol,
                    "名前": info["name"],
                    "現在値": f"${current_price:.2f}",
                    "狙い指値(-2%)": f"${target_limit:.2f}",
                    "予算配分": f"${allocated_usd:.0f}",
                    "推奨株数": f"{shares} 株"
                })
            else:
                st.error(f"{symbol} のデータが取得できませんでした。")
        except Exception as e:
            st.error(f"エラー: {e}")

# 5. 結果表示
if results:
    df = pd.DataFrame(results)
    st.table(df)
    st.success("計算完了！この『推奨株数』を参考に注文を入れてください。")
else:
    st.warning("データが取得できませんでした。しばらく待ってから再読み込みしてください。")

st.info("💡 ヒント: 市場が動いている時は、右上のメニューから「Rerun」を押すと最新価格に更新されます。")
