import os
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup


OUTPUT_DIR  = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "market_indicators.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def calculate_rsi(data: pd.Series, window: int = 14) -> float | None:
    try:
        delta = data.diff()
        gain  = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs    = gain / loss
        rsi   = 100 - (100 / (1 + rs))
        val   = rsi.iloc[-1]
        return round(float(val), 2) if not pd.isna(val) else None
    except Exception:
        return None


def get_qqq_data():
    try:
        qqq  = yf.Ticker("QQQ")
        hist = qqq.history(period="210d")
        if hist.empty or len(hist) < 200:
            return None, None, None, None
        close       = hist["Close"]
        price       = round(float(close.iloc[-1]), 2)
        sma200      = round(float(close.tail(200).mean()), 2)
        deviation   = round((price - sma200) / sma200 * 100, 2)   # 이격률
        daily_ret   = round(float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100), 2)
        return price, sma200, deviation, daily_ret
    except Exception:
        return None, None, None, None


def get_vix():
    for symbol in ["^VIX", "VIX", "VIXY"]:
        try:
            data = yf.Ticker(symbol).history(period="5d")
            if not data.empty:
                return round(float(data["Close"].iloc[-1]), 2)
        except Exception:
            pass
    return None


def get_usd_krw():
    """USD/KRW 최신값. 야후 환율 일봉 종가는 하루 중간에 멈추는 경우가 있어 15분봉 마지막 값 사용"""
    try:
        t = yf.Ticker("USDKRW=X")
        bars = t.history(period="5d", interval="15m")["Close"].dropna()
        if bars.empty:
            bars = t.history(period="5d")["Close"].dropna()
        if not bars.empty:
            return round(float(bars.iloc[-1]), 2)
    except Exception:
        pass
    return None

def get_us30y_yield():
    try:
        data = yf.Ticker("^TYX").history(period="5d")
        if not data.empty:
            return round(float(data["Close"].iloc[-1]), 3)
    except Exception:
        pass
    return None


def get_sp500_rsi():
    try:
        data = yf.Ticker("SPY").history(period="50d")["Close"]
        return calculate_rsi(data)
    except Exception:
        return None


def fetch_fgi():
    try:
        url  = "https://feargreedmeter.com/"
        hdrs = {"User-Agent": "Mozilla/5.0"}
        res  = requests.get(url, headers=hdrs, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        el   = soup.find("div", class_="text-center text-4xl font-semibold mb-1 text-white")
        if el and el.text.strip().isdigit():
            return int(el.text.strip())
    except Exception:
        pass
    return None

CBOE_PCR_URL = "https://cdn.cboe.com/data/us/options/market_statistics/daily/{date}_daily_options"


def get_market_date() -> str | None:
    """VIX·QQQ 종가가 가리키는 미국 거래일 (yfinance 마지막 봉 날짜, YYYY-MM-DD)"""
    try:
        hist = yf.Ticker("SPY").history(period="5d")
        if not hist.empty:
            return hist.index[-1].strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def fetch_pci(market_date: str | None) -> float | None:
    """CBOE 일별 통계 JSON에서 지정한 거래일의 Equity Put/Call Ratio.
    아직 게시되지 않은 날(403/404)이면 None → 다음 실행 때 다시 채움.
    (예전 HTML 페이지는 날짜 지정 없이 '게시된 최신일'을 보여줘서
     수집 시각에 따라 당일/전일 값이 섞여 들어갔음)"""
    if not market_date:
        return None
    try:
        url = CBOE_PCR_URL.format(date=market_date)
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if res.status_code != 200:
            return None
        for item in res.json().get("ratios", []):
            if item.get("name", "").upper() == "EQUITY PUT/CALL RATIO":
                return round(float(item["value"]), 4)
        return None
    except Exception:
        return None


def fill_missing_pci(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """최근 lookback개 행 중 put_call_ratio가 빈 행을 그 행의 market_date 값으로 채움"""
    if "market_date" not in df.columns:
        return df
    for idx in df.tail(lookback).index:
        if pd.isna(df.at[idx, "put_call_ratio"]) and pd.notna(df.at[idx, "market_date"]):
            val = fetch_pci(str(df.at[idx, "market_date"]))
            if val is not None:
                df.at[idx, "put_call_ratio"] = val
                print(f"  PCI 보충: {df.at[idx, 'market_date']} → {val}")
            time.sleep(0.5)
    return df

def collect() -> dict:
    now = datetime.now(timezone.utc)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')} UTC] 지표 수집 시작")

    qqq_price, qqq_sma200, qqq_deviation, qqq_daily_ret = get_qqq_data()
    print(f"  QQQ: {qqq_price} | SMA200: {qqq_sma200} | 이격률: {qqq_deviation}% | 일수익: {qqq_daily_ret}%")

    vix = get_vix()
    print(f"  VIX: {vix}")

    fgi = fetch_fgi()
    print(f"  FGI: {fgi}")

    # PCI는 VIX·QQQ와 같은 거래일 값으로 수집 (아직 미게시면 빈칸, 다음 실행 때 보충)
    market_date = get_market_date()
    pci = fetch_pci(market_date)
    print(f"  거래일: {market_date} | PCI: {pci}")

    rsi = get_sp500_rsi()
    print(f"  SPY RSI: {rsi}")

    usd_krw = get_usd_krw()
    print(f"  USD/KRW: {usd_krw}")


    us30y = get_us30y_yield()
    print(f"  US 30Y Yield: {us30y}")

    row = {
        "date":              now.strftime("%Y-%m-%d"),
        "collected_at_utc":  now.strftime("%Y-%m-%d %H:%M:%S"),
        "market_date":       market_date,     # 종가 기준 미국 거래일

        # 공포&탐욕
        "fgi":               fgi,

        # 변동성
        "vix":               vix,

        # QQQ
        "qqq_price":         qqq_price,
        "qqq_sma200":        qqq_sma200,
        "qqq_vs_sma200_pct": qqq_deviation,   # + 면 SMA 위, - 면 아래
        "qqq_daily_return":  qqq_daily_ret,   # 나스닥 전일 대비 수익률 (상관관계 분석용)

        # 옵션 심리
        "put_call_ratio":    pci,

        # S&P500 RSI
        "spy_rsi":           rsi,

        # 환율
        "usd_krw":           usd_krw,

        # 30년 국채
        "us30y":     us30y,      
    }
    return row


def append_to_csv(row: dict):
    """CSV가 없으면 생성, 있으면 같은 날짜 중복 체크 후 append"""
    new_df = pd.DataFrame([row])

    if os.path.exists(OUTPUT_FILE):
        existing = pd.read_csv(OUTPUT_FILE)

        # 같은 날짜 행이 이미 있으면 덮어쓰기 (재실행 안전)
        existing = existing[existing["date"] != row["date"]]
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    combined = fill_missing_pci(combined)
    combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ 저장 완료 → {OUTPUT_FILE}  (총 {len(combined)}행)")


if __name__ == "__main__":
    row = collect()
    append_to_csv(row)
