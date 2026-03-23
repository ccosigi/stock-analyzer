"""
collect_daily_indicators.py
───────────────────────────
GitHub Actions에서 매일 실행되는 시장 지표 수집 스크립트.
app.py의 1페이지(시장 감정 탭) 지표 6개를 수집해서
data/market_indicators.csv 에 누적 저장합니다.

수집 지표:
  - 공포&탐욕 지수 (FGI)
  - VIX
  - QQQ 현재가 / 200일 이동평균 / 이격률(%)
  - Put/Call 비율 (PCI)
  - S&P500 RSI
  - 원달러 환율 / 전일대비 변화량 / 변화율
  - 나스닥(QQQ) 전일 대비 수익률 (나중에 상관관계 분석용)
"""

import os
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
OUTPUT_DIR  = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "market_indicators.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ──────────────────────────────────────────
# 수집 함수 (app.py 로직 그대로 복사)
# ──────────────────────────────────────────

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
    """QQQ 현재가, 200일 이동평균, 이격률, 전일 대비 수익률"""
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
    try:
        data = yf.Ticker("USDKRW=X").history(period="5d")
        if len(data) >= 2:
            rate   = round(float(data["Close"].iloc[-1]), 2)
            change = round(float(data["Close"].iloc[-1] - data["Close"].iloc[-2]), 2)
            pct    = round(change / float(data["Close"].iloc[-2]) * 100, 4)
            return rate, change, pct
    except Exception:
        pass
    return None, None, None


def get_sp500_rsi():
    try:
        data = yf.Ticker("SPY").history(period="50d")["Close"]
        return calculate_rsi(data)
    except Exception:
        return None


def fetch_fgi():
    """feargreedmeter.com 스크래핑"""
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


def fetch_pci():
    """ycharts Put/Call 비율 스크래핑"""
    try:
        url  = "https://ycharts.com/indicators/cboe_equity_put_call_ratio"
        hdrs = {"User-Agent": "Mozilla/5.0"}
        res  = requests.get(url, headers=hdrs, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for td in soup.find_all("td", class_="col-6"):
            try:
                return round(float(td.text.strip().replace(",", "")), 4)
            except ValueError:
                continue
    except Exception:
        pass
    return None


# ──────────────────────────────────────────
# 메인 수집
# ──────────────────────────────────────────

def collect() -> dict:
    now = datetime.now(timezone.utc)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')} UTC] 지표 수집 시작")

    qqq_price, qqq_sma200, qqq_deviation, qqq_daily_ret = get_qqq_data()
    print(f"  QQQ: {qqq_price} | SMA200: {qqq_sma200} | 이격률: {qqq_deviation}% | 일수익: {qqq_daily_ret}%")

    vix = get_vix()
    print(f"  VIX: {vix}")

    fgi = fetch_fgi()
    print(f"  FGI: {fgi}")

    # PCI는 rate limit 조심해서 살짝 딜레이
    time.sleep(2)
    pci = fetch_pci()
    print(f"  PCI: {pci}")

    rsi = get_sp500_rsi()
    print(f"  SPY RSI: {rsi}")

    usd_krw, usd_krw_chg, usd_krw_pct = get_usd_krw()
    print(f"  USD/KRW: {usd_krw} ({usd_krw_chg}, {usd_krw_pct}%)")

    row = {
        "date":              now.strftime("%Y-%m-%d"),
        "collected_at_utc":  now.strftime("%Y-%m-%d %H:%M:%S"),

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
        "usd_krw_change":    usd_krw_chg,
        "usd_krw_change_pct":usd_krw_pct,
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

    combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ 저장 완료 → {OUTPUT_FILE}  (총 {len(combined)}행)")


if __name__ == "__main__":
    row = collect()
    append_to_csv(row)
