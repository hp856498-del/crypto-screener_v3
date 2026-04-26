import streamlit as st
import pandas as pd
import requests
import ta
from datetime import datetime
import pytz
import time

st.set_page_config(page_title="RSI Divergence Screener", layout="wide")

st.title("🔥 RSI Divergence Screener (Accurate Version)")

# ================= INPUTS =================
date = st.date_input("Select Date")
coin_limit = st.selectbox("Select Coins", [50, 100, 200])
timeframe = st.selectbox("Select Timeframe", ["15m", "30m", "1h", "4h"])

# ================= TIMEZONE =================
IST = pytz.timezone("Asia/Kolkata")

# ================= GET TOP COINS =================
def get_top_coins(limit):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()

    usdt_pairs = [d for d in data if d['symbol'].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)

    return [d['symbol'] for d in sorted_pairs[:limit]]

# ================= FETCH DATA =================
def get_klines(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
    data = requests.get(url).json()

    df = pd.DataFrame(data, columns=[
        "time","open","high","low","close","volume",
        "ct","qav","nt","tb","tq","ignore"
    ])

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    df["time"] = pd.to_datetime(df["time"], unit='ms')
    df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(IST)

    return df

# ================= PIVOT DETECTION =================
def find_pivots(df, left=3, right=3):
    pivots_high = []
    pivots_low = []

    for i in range(left, len(df)-right):
        high = df["high"][i]
        low = df["low"][i]

        if high == max(df["high"][i-left:i+right+1]):
            pivots_high.append(i)

        if low == min(df["low"][i-left:i+right+1]):
            pivots_low.append(i)

    return pivots_high, pivots_low

# ================= DIVERGENCE =================
def check_divergence(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    piv_high, piv_low = find_pivots(df)

    results = []

    # ===== BULLISH =====
    for i in range(1, len(piv_low)):
        prev = piv_low[i-1]
        curr = piv_low[i]

        price_prev = df["low"][prev]
        price_curr = df["low"][curr]

        rsi_prev = df["rsi"][prev]
        rsi_curr = df["rsi"][curr]

        # lower low + higher RSI
        if price_curr < price_prev and rsi_curr > rsi_prev:
            results.append({
                "time": df["time"][curr],
                "type": "Bullish"
            })

    # ===== BEARISH =====
    for i in range(1, len(piv_high)):
        prev = piv_high[i-1]
        curr = piv_high[i]

        price_prev = df["high"][prev]
        price_curr = df["high"][curr]

        rsi_prev = df["rsi"][prev]
        rsi_curr = df["rsi"][curr]

        # higher high + lower RSI
        if price_curr > price_prev and rsi_curr < rsi_prev:
            results.append({
                "time": df["time"][curr],
                "type": "Bearish"
            })

    return results

# ================= SCAN =================
if st.button("Scan"):

    coins = get_top_coins(coin_limit)
    results = []

    progress = st.progress(0)

    for i, coin in enumerate(coins):
        try:
            df = get_klines(coin, timeframe)
            divs = check_divergence(df)

            for d in divs:
                if d["time"].date() == date:
                    results.append({
                        "Coin": coin,
                        "Timeframe": timeframe,
                        "Time (IST)": d["time"],
                        "Type": d["type"]
                    })

        except:
            pass

        progress.progress((i+1)/len(coins))

    # ===== OUTPUT =====
    if results:
        df_res = pd.DataFrame(results)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.warning("No divergence found")