from tabs.history_tab import history_tab
from tabs.market_sentiment_tab import market_sentiment_tab
from tabs.nday_analysis_tab import nday_analysis_tab
from tabs.sp500_screener_tab import sp500_screener_tab

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import warnings
warnings.filterwarnings('ignore')

try:
    from stock_library import get_stock_count
    print(f"주식 라이브러리 로드 완료! {get_stock_count()}개 종목 지원")
except ImportError as e:
    print(f"stock_library.py 파일을 찾을 수 없습니다: {e}")

try:
    from stock_library import get_sp500_stock_count
    print(f"S&P 500 라이브러리 로드 완료! {get_sp500_stock_count()}개 종목 지원")
except ImportError as e:
    print(f"stock_library.py 파일을 찾을 수 없습니다: {e}")


st.set_page_config(
    page_title="주식 분석 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1.5rem;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #333;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .bullish {
        border-left-color: #28a745 !important;
        background-color: #d4edda;
    }
    .bearish {
        border-left-color: #dc3545 !important;
        background-color: #f8d7da;
    }
    .neutral {
        border-left-color: #ffc107 !important;
        background-color: #fff3cd;
    }
    .win {
        border-left-color: #28a745 !important;
        background-color: #f8d7da;
    }
    .lose {
        border-left-color: #dc3545 !important;
        background-color: #d4edda;
    }
    .info-box {
        background-color: #f8f9fa;
        color: #212529;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info-box h4 { color: #495057; margin-bottom: 0.5rem; }
    .info-box ul { color: #6c757d; margin-bottom: 0; }
    .info-box li { margin-bottom: 0.3rem; color: #495057; }
    .result-box {
        background-color: #ffffff;
        color: #212529;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #007bff;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .result-box h3 { color: #495057; margin-bottom: 0.5rem; }
    .result-box h1 { color: #212529; margin-bottom: 0.5rem; }
    .result-box p  { color: #6c757d; margin-bottom: 0; }
    .win-box  { background-color: #fff8f8; border-color: #dc3545; color: #721c24; }
    .win-box  h3, .win-box  h1 { color: #721c24; }
    .win-box  p { color: #6c7b6f; }
    .lose-box { background-color: #f8fff9; border-color: #28a745; color: #155724; }
    .lose-box h3, .lose-box h1 { color: #155724; }
    .lose-box p { color: #856969; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { height: 60px; padding: 0 24px; font-weight: 600; }
    .screener-table {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .stock-highlight {
        background-color: #e8f5e8;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
        padding: 0.8rem;
        border-radius: 8px;
    }
    @media (max-width: 768px) {
        .main-header { font-size: 1.6rem; }
        .metric-container { padding: 0.8rem; margin: 0.3rem 0; }
        .result-box { padding: 1rem; }
        .info-box { padding: 0.8rem; font-size: 0.9rem; }
        .info-box h4 { font-size: 1rem; }
        .stTabs [data-baseweb="tab"] { padding: 0 16px; font-size: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<h1 class="main-header">📈 주식 시장 분석 대시보드</h1>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 시장 감정", "📉 하락 분석", "🎯 S&P500 스크리너", "히스토리"])

    with tab1:
        market_sentiment_tab()
    with tab2:
        nday_analysis_tab()
    with tab3:
        sp500_screener_tab()
    with tab4:
        history_tab()

    st.markdown("---")
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.markdown(f"""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>📊 <strong>주식 분석 대시보드</strong> | 마지막 업데이트: {current_time}</p>
        <p>🌏 <strong>지원 주식</strong>: 미국 주식 (QQQ, SPY, AAPL 등) + 한국 주식 + S&P500 스크리너</p>
        <p>⚠️ <em>이 도구는 참고 용도이며, 실제 투자 결정의 유일한 근거로 사용하지 마세요.</em></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
