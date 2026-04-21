import streamlit as st
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import numpy as np


# ── 데이터 fetch ─────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_qqq_data():
    try:
        qqq = yf.Ticker("QQQ")
        data = qqq.history(period="1d")
        if data.empty:
            return None, None, None
        qqq_price = data['Close'].iloc[-1]
        qqq_history = qqq.history(period="200d")['Close']
        if len(qqq_history) < 200:
            return None, None, None
        qqq_sma = qqq_history.mean()
        qqq_52w = qqq.history(period="1y")['Close']
        qqq_all_time_high = qqq_52w.max() if not qqq_52w.empty else None
        return qqq_price, qqq_sma, qqq_all_time_high
    except Exception:
        return None, None, None

@st.cache_data(ttl=60)
def get_vix_data():
    try:
        for symbol in ["^VIX", "VIX", "VIXY"]:
            try:
                vix = yf.Ticker(symbol)
                data = vix.history(period="5d")
                if not data.empty and len(data) > 0:
                    return data['Close'].iloc[-1]
            except:
                continue
        return None
    except Exception:
        return None

@st.cache_data(ttl=60)
def get_usd_krw_rate():
    try:
        usd_krw = yf.Ticker("USDKRW=X")
        data = usd_krw.history(period="5d")
        if not data.empty and len(data) >= 2:
            current_rate = data['Close'].iloc[-1]
            prev_rate = data['Close'].iloc[-2]
            change_amount = current_rate - prev_rate
            change_pct = (change_amount / prev_rate) * 100
            return current_rate, change_amount, change_pct
        return None, None, None
    except Exception:
        return None, None, None

@st.cache_data(ttl=300)
def fetch_fgi():
    try:
        url = 'https://feargreedmeter.com/'
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        fgi_element = soup.find('div', class_='text-center text-4xl font-semibold mb-1 text-white')
        if fgi_element:
            fgi_text = fgi_element.text.strip()
            return int(fgi_text) if fgi_text.isdigit() else None
        return None
    except Exception:
        return None

@st.cache_data(ttl=300)
def fetch_pci():
    try:
        url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        td_elements = soup.find_all('td', class_='col-6')
        for td in td_elements:
            try:
                return float(td.text.strip().replace(',', ''))
            except ValueError:
                continue
        return None
    except Exception:
        return None


# ── 해석 함수 ────────────────────────────────────────────────────────

def interpret_fgi(fgi):
    if fgi is None:
        return "데이터 없음", "neutral"
    if fgi <= 25:
        return "극심한 공포 (매수 신호)", "bearish"
    elif fgi <= 45:
        return "공포 (매수 신호)", "bearish"
    elif fgi <= 55:
        return "중립적 (유지 또는 관망)", "neutral"
    elif fgi <= 75:
        return "탐욕적 (매도 신호)", "bullish"
    else:
        return "극도로 탐욕적 (매도 신호)", "bullish"

def interpret_vix(vix):
    if vix is None:
        return "데이터 없음", "neutral"
    if vix < 15:
        return "변동성 낮음 (상승장) 매도 신호", "bullish"
    elif vix < 25:
        return "변동성 중간 (중립)", "neutral"
    else:
        return "변동성 높음 (하락장) 매수 신호", "bearish"

def interpret_pci(pci):
    if pci is None:
        return "데이터 없음", "neutral"
    if pci > 0.95:
        return "하락 베팅 증가 (매수 신호)", "bearish"
    elif pci < 0.65:
        return "상승 베팅 증가 (매도 신호)", "bullish"
    else:
        return "중립적 상태", "neutral"

def interpret_rsi(rsi):
    if rsi is None:
        return "데이터 없음", "neutral"
    if rsi < 30:
        return "과매도 (매수 신호)", "bearish"
    elif rsi > 70:
        return "과매수 (매도 신호)", "bullish"
    else:
        return "중립", "neutral"

def interpret_usd_krw(rate, change_amount, change_pct):
    if rate is None:
        return "데이터 없음", "neutral"
    if change_amount > 0:
        amount_text = f"(↗️ {change_amount:.1f}원, +{change_pct:.2f}%)"
        return f"전일 대비 {amount_text}", "bearish"
    elif change_amount < 0:
        amount_text = f"(↘️ {abs(change_amount):.1f}원, {change_pct:.2f}%)"
        return f"전일 대비 {amount_text}", "bullish"
    else:
        return "전일 대비 (➡️ 보합)", "neutral"


# ── UI 헬퍼 ─────────────────────────────────────────────────────────

def display_metric(title, value, interpretation, sentiment):
    css_class = f"metric-container {sentiment}"
    st.markdown(f"""
    <div class="{css_class}">
        <h3 style="margin-bottom: 0.5rem; color: #333;">{title}</h3>
        <h2 style="margin-bottom: 0.3rem; color: #000;">{value}</h2>
        <p style="margin-bottom: 0; font-size: 1rem; color: #555;">{interpretation}</p>
    </div>
    """, unsafe_allow_html=True)


# ── 레버리지 전략 상수 ───────────────────────────────────────────────

STRATEGY_STEPS = [
    ("평상시",  0,  "QQQ 100%",           "#d4edda", "#28a745", "#155724"),
    ("−5%",     5,  "QQQ 90% / QLD 10%",  "#e8f5e9", "#43a85a", "#1a5c2a"),
    ("−10%",   10,  "QQQ 70% / QLD 30%",  "#fff3cd", "#ffc107", "#856404"),
    ("−15%",   15,  "QQQ 40% / QLD 60%",  "#ffe8b0", "#fd9800", "#7d4200"),
    ("−20%",   20,  "QLD 100%",            "#ffd9a0", "#fd7e14", "#6d3000"),
    ("−25%",   25,  "QLD 50% / TQQQ 50%", "#f8d7da", "#dc3545", "#721c24"),
    ("−30%",   30,  "TQQQ 100%",           "#f5b0b5", "#a71d2a", "#4e0a10"),
]

def get_leverage_strategy(drop_pct):
    if drop_pct is None:
        return None, None, None, None, None
    for i, (label, threshold, alloc, bg, border, txt) in enumerate(STRATEGY_STEPS):
        next_threshold = STRATEGY_STEPS[i+1][1] if i+1 < len(STRATEGY_STEPS) else 999
        if drop_pct < next_threshold:
            return label, alloc, bg, border, txt
    last = STRATEGY_STEPS[-1]
    return last[0], last[2], last[3], last[4], last[5]


# ── 탭 메인 함수 ─────────────────────────────────────────────────────

def market_sentiment_tab():
    st.markdown('''
    <div class="sub-header" style="color: inherit;">
        📊 실시간 시장 지표
    </div>
    ''', unsafe_allow_html=True)

    qqq_price, qqq_sma, qqq_high = get_qqq_data()
    vix = get_vix_data()
    fgi = fetch_fgi()
    pci = fetch_pci()
    usd_krw_rate, usd_krw_change_amount, usd_krw_change_pct = get_usd_krw_rate()

    try:
        spy_data = yf.Ticker("SPY").history(period="50d")["Close"]
        delta = spy_data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = rsi_series.iloc[-1] if not rsi_series.empty else None
    except:
        rsi = None

    col1, col2 = st.columns([1, 1])

    with col1:
        if fgi is not None:
            fgi_interp, fgi_sentiment = interpret_fgi(fgi)
            display_metric("😨 공포 & 탐욕 지수", f"{fgi}/100", fgi_interp, fgi_sentiment)
        else:
            display_metric("😨 공포 & 탐욕 지수", "N/A", "데이터 로딩 실패", "neutral")

        if vix is not None:
            vix_interp, vix_sentiment = interpret_vix(vix)
            display_metric("📈 VIX (변동성 지수)", f"{vix:.2f}", vix_interp, vix_sentiment)
        else:
            display_metric("📈 VIX (변동성 지수)", "로딩중...", "데이터 새로고침 중 (잠시 후 다시 시도)", "neutral")

        if qqq_price is not None and qqq_sma is not None:
            price_vs_sma    = "bullish" if qqq_price > qqq_sma else "bearish"
            trend_text      = "상승 추세" if price_vs_sma == "bullish" else "하락 추세"
            percentage_diff = ((qqq_price - qqq_sma) / qqq_sma) * 100
            sma_bg     = "#d4edda" if price_vs_sma == "bullish" else "#f8d7da"
            sma_border = "#28a745" if price_vs_sma == "bullish" else "#dc3545"
            sma_txt    = "#155724" if price_vs_sma == "bullish" else "#721c24"
            diff_sign   = "+" if percentage_diff >= 0 else ""
            trend_arrow = "▲" if percentage_diff >= 0 else "▼"
            above_below = "위" if price_vs_sma == "bullish" else "아래"
            st.markdown(f"""
            <div class="metric-container" style="background:{sma_bg}; border-left-color:{sma_border}; min-height:160px;">
                <h3 style="margin-bottom:0.5rem; color:#333;">🚀 QQQ vs 200일 이동평균</h3>
                <div style="display:flex; gap:1.5rem; align-items:flex-end; flex-wrap:nowrap; margin-bottom:0.3rem;">
                    <div>
                        <p style="margin:0; font-size:0.78rem; color:#555;">현재가</p>
                        <p style="margin:0; font-size:1.75rem; font-weight:bold; color:#000;">${qqq_price:.2f}</p>
                    </div>
                    <div>
                        <p style="margin:0; font-size:0.78rem; color:#555;">200일 평균</p>
                        <p style="margin:0; font-size:1.75rem; font-weight:bold; color:#000;">${qqq_sma:.2f}</p>
                    </div>
                    <div>
                        <p style="margin:0; font-size:0.78rem; color:#555;">대비</p>
                        <p style="margin:0; font-size:1.75rem; font-weight:bold; color:{sma_border};">{trend_arrow} {diff_sign}{percentage_diff:.1f}%</p>
                    </div>
                </div>
                <p style="margin:0; font-size:1rem; color:#555;">{trend_text} — 200일 이동평균 {above_below}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            display_metric("🚀 QQQ vs 200일 이동평균", "N/A", "데이터 로딩 실패", "neutral")

    with col2:
        if pci is not None:
            pci_interp, pci_sentiment = interpret_pci(pci)
            display_metric("⚖️ Put/Call 비율", f"{pci:.3f}", pci_interp, pci_sentiment)
        else:
            display_metric("⚖️ Put/Call 비율", "N/A", "데이터 로딩 실패", "neutral")

        if rsi is not None:
            rsi_interp, rsi_sentiment = interpret_rsi(rsi)
            display_metric("📊 RSI (S&P500)", f"{rsi:.1f}", rsi_interp, rsi_sentiment)
        else:
            display_metric("📊 RSI (S&P500)", "N/A", "데이터 로딩 실패", "neutral")

        if usd_krw_rate is not None:
            usd_krw_interp, usd_krw_sentiment = interpret_usd_krw(usd_krw_rate, usd_krw_change_amount, usd_krw_change_pct)
            display_metric("🔁 원달러 환율", f"₩{usd_krw_rate:.2f}", usd_krw_interp, usd_krw_sentiment)
        else:
            display_metric("🔁 원달러 환율", "N/A", "데이터 로딩 실패", "neutral")

    # ── QQQ 레버리지 전략 패널 ─────────────────────────────────────
    st.markdown("---")
    st.markdown('''
    <div class="sub-header" style="color: inherit;">
        QQQ 레버리지 전환 원칙
    </div>
    ''', unsafe_allow_html=True)

    if qqq_price is not None and qqq_high is not None:
        drop_pct = max(0.0, ((qqq_high - qqq_price) / qqq_high) * 100)
        stage_label, portfolio, summary_bg, border_color, txt_color = get_leverage_strategy(drop_pct)

        st.markdown(f"""
        <div class="metric-container" style="background:{summary_bg}; border-left-color:{border_color};">
            <div style="display:flex; flex-wrap:wrap; gap:2rem; align-items:center;">
                <div>
                    <p style="margin:0; font-size:0.82rem; color:#555;">QQQ 현재가</p>
                    <p style="margin:0; font-size:1.6rem; font-weight:bold; color:#111;">${qqq_price:.2f}</p>
                </div>
                <div>
                    <p style="margin:0; font-size:0.82rem; color:#555;">52주 전고점</p>
                    <p style="margin:0; font-size:1.6rem; font-weight:bold; color:#111;">${qqq_high:.2f}</p>
                </div>
                <div>
                    <p style="margin:0; font-size:0.82rem; color:#555;">전고점 대비 하락률</p>
                    <p style="margin:0; font-size:1.6rem; font-weight:bold; color:{border_color};">−{drop_pct:.1f}%</p>
                </div>
                <div style="flex:1; min-width:180px;">
                    <p style="margin:0; font-size:0.82rem; color:#555;">현재 구간 · 권장 포트폴리오</p>
                    <p style="margin:0; font-size:1.05rem; font-weight:bold; color:{txt_color};">
                        {stage_label} &nbsp;→&nbsp; {portfolio}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        rows_html = ""
        for label, threshold, alloc, row_bg, row_border, row_txt in STRATEGY_STEPS:
            is_current = (label == stage_label)
            if is_current:
                fw, marker = "bold", "◀ 현재"
                cell_style = f"background:{row_bg}; border-left:4px solid {row_border};"
            else:
                fw, marker = "normal", ""
                cell_style = f"background:{row_bg}; opacity:0.6;"
            rows_html += f"""
            <tr style="{cell_style}">
                <td style="padding:7px 12px; font-weight:{fw}; color:{row_txt}; border-left:4px solid {row_border};">{label}</td>
                <td style="padding:7px 12px; font-weight:{fw}; color:{row_txt};">{alloc}</td>
                <td style="padding:7px 12px; font-weight:bold; color:{row_border}; white-space:nowrap;">{marker}</td>
            </tr>"""

        with st.expander("📋 구간별 권장 포트폴리오 보기", expanded=False):
            st.markdown(f"""
            <table style="width:100%; border-collapse:collapse; font-size:0.93rem; border-radius:8px; overflow:hidden; margin-top:0.5rem;">
                <thead>
                    <tr style="background:#e9ecef;">
                        <th style="padding:8px 12px; text-align:left; color:#333;">하락 구간</th>
                        <th style="padding:8px 12px; text-align:left; color:#333;">권장 포트폴리오</th>
                        <th style="padding:8px 12px; text-align:left;"></th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            <p style="font-size:0.78rem; color:#888; margin-top:0.5rem;">
                ※ 52주 최고가 기준 하락률 &nbsp;|&nbsp; 하락·회복 동일 원칙 적용 &nbsp;|&nbsp;
                QLD = 나스닥 2배 레버리지 &nbsp;|&nbsp; TQQQ = 나스닥 3배 레버리지
            </p>
            """, unsafe_allow_html=True)
    else:
        st.warning("QQQ 데이터를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")

    st.markdown("---")

    with st.expander("📖 지표 설명", expanded=False):
        st.markdown("""
        <div class="info-box">
            <h4>📖 지표 설명</h4>
            <ul>
                <li><strong>공포 & 탐욕 지수</strong>: 0-100 범위의 시장 심리 지표 (0=극도공포, 100=극도탐욕)</li>
                <li><strong>VIX</strong>: 시장 변동성 예상 지수 (낮을수록 안정, 높을수록 불안)</li>
                <li><strong>Put/Call 비율</strong>: 풋옵션 대비 콜옵션 거래량</li>
                <li><strong>RSI</strong>: 상대강도지수 (30 이하 과매도, 70 이상 과매수)</li>
                <li><strong>QQQ vs 200일 이동 평균선</strong>: 나스닥 ETF의 장기 추세 분석</li>
                <li><strong>원달러 환율</strong>: USD/KRW 환율 (상승시 원화약세, 하락시 원화강세)</li>
            </ul>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #6c757d;">
                💡 <strong>팁</strong>: 여러 지표를 종합적으로 해석하여 투자 판단에 활용하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
