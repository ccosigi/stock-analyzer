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
    from stock_library import (
        KOREAN_STOCKS, 
        get_ticker_from_name, 
        process_ticker_input,
        get_stock_count
    )
    print(f"주식 라이브러리 로드 완료! {get_stock_count()}개 종목 지원")
except ImportError as e:
    print(f" stock_library.py 파일을 찾을 수 없습니다: {e}")
    
try:
    from stock_library import (
        get_sp500_tickers,
        get_sp500_company_name,
        get_sp500_stocks_by_sector,
        get_sp500_stock_count
    )
    print(f"S&P 500 라이브러리 로드 완료! {get_sp500_stock_count()}개 종목 지원")
except ImportError as e:
    print(f"stock_library.py 파일을 찾을 수 없습니다: {e}")
    
    def get_sp500_tickers():
        return ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN"]  # 최소한의 종목들
    def get_sp500_company_name(ticker):
        return ticker
    def get_sp500_stock_count():
        return 5

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
    .info-box h4 {
        color: #495057;
        margin-bottom: 0.5rem;
    }
    .info-box ul {
        color: #6c757d;
        margin-bottom: 0;
    }
    .info-box li {
        margin-bottom: 0.3rem;
        color: #495057;
    }
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
    .result-box h3 {
        color: #495057;
        margin-bottom: 0.5rem;
    }
    .result-box h1 {
        color: #212529;
        margin-bottom: 0.5rem;
    }
    .result-box p {
        color: #6c757d;
        margin-bottom: 0;
    }
    .win-box {
        background-color: #fff8f8;
        border-color: #dc3545;
        color: #721c24;
    }
    .win-box h3, .win-box h1 {
        color: #721c24;
    }
    .win-box p {
        color: #6c7b6f;
    }
    .lose-box {
        background-color: #f8fff9;
        border-color: #28a745;
        color: #155724;
    }
    .lose-box h3, .lose-box h1 {
        color: #155724;
    }
    .lose-box p {
        color: #856969;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0 24px;
        font-weight: 600;
    }
    
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
        .main-header {
            font-size: 1.6rem;
        }
        .metric-container {
            padding: 0.8rem;
            margin: 0.3rem 0;
        }
        .result-box {
            padding: 1rem;
        }
        .info-box {
            padding: 0.8rem;
            font-size: 0.9rem;
        }
        .info-box h4 {
            font-size: 1rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0 16px;
            font-size: 0.9rem;
        }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)  # 1시간 캐시
def get_sp500_tickers_cached():
    """캐시된 S&P 500 종목 리스트를 가져오는 함수"""
    try:
   
        return get_sp500_tickers()
    except:
      
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_table = tables[0]
            return sp500_table['Symbol'].tolist()
        except:
       
            return get_sp500_tickers()

def calculate_rsi(prices, window=14):
    
    if len(prices) < window + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    
    delta = prices.diff()
    
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
  
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    
   
    for i in range(window, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window-1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window-1) + loss.iloc[i]) / window
    
   
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    
    # 볼린저 밴드 위치 (0이 하단, 1이 상단)
    bb_position = (prices - lower_band) / (upper_band - lower_band)
    
    # 볼린저 밴드 폭 (표준화)
    bb_width = (upper_band - lower_band) / sma
    
    return bb_position, bb_width, upper_band, lower_band, sma

def analyze_stock(ticker):
    
    try:
        stock = yf.Ticker(ticker)
        
      
        hist = stock.history(period="2y")
        
        if hist.empty or len(hist) < 252: 
            return None
            
        prices = hist['Close']
        
      
        rsi = calculate_rsi(prices)
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else None
        
      
        bb_position, bb_width, upper_band, lower_band, sma = calculate_bollinger_bands(prices)
        current_bb_position = bb_position.iloc[-1] if len(bb_position) > 0 else None
        current_bb_width = bb_width.iloc[-1] if len(bb_width) > 0 else None
        
        
        bb_width_52w_avg = bb_width.rolling(252).mean().iloc[-1] if len(bb_width) >= 252 else None
        
        
        current_price = prices.iloc[-1]
        current_upper = upper_band.iloc[-1] if len(upper_band) > 0 else None
        current_lower = lower_band.iloc[-1] if len(lower_band) > 0 else None
        current_sma = sma.iloc[-1] if len(sma) > 0 else None
        
       
        if (current_rsi is not None and current_bb_position is not None and 
            current_bb_width is not None and bb_width_52w_avg is not None):
            
            rsi_condition = current_rsi < 40
            bb_position_condition = current_bb_position < 0.5  # 하단 근처
            bb_width_condition = current_bb_width < bb_width_52w_avg
            
            if rsi_condition and bb_position_condition and bb_width_condition:
                return {
                    'ticker': ticker,
                    'price': current_price,
                    'rsi': current_rsi,
                    'bb_position': current_bb_position,
                    'bb_width': current_bb_width,
                    'bb_width_52w_avg': bb_width_52w_avg,
                    'upper_band': current_upper,
                    'lower_band': current_lower,
                    'sma': current_sma,
                    'meets_criteria': True
                }
        
        return None
        
    except Exception as e:
        return None

def get_stock_info(ticker):
    """주식 기본 정보 가져오기"""
    try:
        local_name = get_sp500_company_name(ticker)
        if local_name != "Unknown":
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'name': local_name,
                'sector': info.get('sector', 'N/A'),
                'market_cap': info.get('marketCap', 'N/A')
            }
        
    
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'name': info.get('shortName', ticker),
            'sector': info.get('sector', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A')
        }
    except:
        return {'name': ticker, 'sector': 'N/A', 'market_cap': 'N/A'}


@st.cache_data(ttl=60)  # Cache for 1 minute
def get_qqq_data():
    try:
        qqq = yf.Ticker("QQQ")
        data = qqq.history(period="1d")
        if data.empty:
            return None, None
        qqq_price = data['Close'].iloc[-1]
        qqq_history = qqq.history(period="200d")['Close']
        if len(qqq_history) < 200:
            return None, None
        qqq_sma = qqq_history.mean()
        return qqq_price, qqq_sma
    except Exception:
        return None, None

@st.cache_data(ttl=60)
def get_vix_data():
    try:
        vix_symbols = ["^VIX", "VIX", "VIXY"]
        
        for symbol in vix_symbols:
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

@st.cache_data(ttl=300)  # Cache for 5 minutes due to web scraping
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

def calculate_rsi_basic(data, window=14):
    try:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else None
    except:
        return None


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
        arrow = "↗️"
        amount_text = f"(↗️ {change_amount:.1f}원, +{change_pct:.2f}%)"
        sentiment = "bearish"  # 원화 약세
        trend_text = "전일 대비"
    elif change_amount < 0:
        arrow = "↘️"
        amount_text = f"(↘️ {abs(change_amount):.1f}원, {change_pct:.2f}%)"
        sentiment = "bullish"  # 원화 강세
        trend_text = "전일 대비"
    else:
        arrow = "➡️"
        amount_text = "(➡️ 보합)"
        sentiment = "neutral"
        trend_text = "보합"
    
    return f"{trend_text} {amount_text}", sentiment

def get_trading_day_after(data_index, target_date, days_after):
    
    
    
    try:
        target_calendar_date = target_date + pd.Timedelta(days=days_after)
        
        
        future_dates = data_index[data_index >= target_calendar_date]
        
        if len(future_dates) > 0:
            return future_dates[0]
        else:
            return None
    except (KeyError, IndexError):
        return None

def add_nday_later_prices(signal_days, data, days_after):
    
    nday_later_prices = []
    actual_days_list = []
    
    for signal_date in signal_days.index:
        future_date = get_trading_day_after(data.index, signal_date, days_after)
        
        if future_date is not None and future_date in data.index:
            nday_later_prices.append(data.loc[future_date, 'Close'])
            
            actual_days = (future_date - signal_date).days
            actual_days_list.append(actual_days)
        else:
            nday_later_prices.append(None)
            actual_days_list.append(None)
    
    signal_days[f'Price_{days_after}D_Later'] = nday_later_prices
    signal_days[f'Actual_Days_Later'] = actual_days_list
    return signal_days

def find_consecutive_drop_periods(data, analysis_days, drop_threshold):
    signal_periods = []
    
    for i in range(analysis_days, len(data)):
        period_start = i - analysis_days
        period_end = i
        
      
        start_price = data.iloc[period_start]['Close']
        end_price = data.iloc[period_end]['Close']
        
    
        total_drop = ((start_price - end_price) / start_price) * 100
        
        if total_drop >= drop_threshold:
            period_data = {
                'start_date': data.iloc[period_start].name,
                'end_date': data.iloc[period_end].name,
                'start_price': start_price,
                'end_price': end_price,
                'total_drop_pct': total_drop,
                'analysis_days': analysis_days
            }
            signal_periods.append(period_data)
    
    return signal_periods

def display_metric(title, value, interpretation, sentiment):
    css_class = f"metric-container {sentiment}"
    st.markdown(f"""
    <div class="{css_class}">
        <h3 style="margin-bottom: 0.5rem; color: #333;">{title}</h3>
        <h2 style="margin-bottom: 0.3rem; color: #000;">{value}</h2>
        <p style="margin-bottom: 0; font-size: 1rem; color: #555;">{interpretation}</p>  
    </div>
    """, unsafe_allow_html=True)


def market_sentiment_tab():
    st.markdown('<div class="sub-header">📊 실시간 시장 지표</div>', unsafe_allow_html=True)
    
 
    col_refresh, col_auto = st.columns([1, 2])
    with col_refresh:
        if st.button("🔄 새로고침", key="refresh_market"):
            st.cache_data.clear()
            st.rerun()
    
    with col_auto:
        auto_refresh = st.checkbox("자동 새로고침 (60초)", key="auto_refresh")
    
    if auto_refresh:
        st.info("⏰ 60초마다 자동으로 업데이트됩니다.")
        
    with st.spinner("시장 데이터 로딩 중..."):
       
        qqq_price, qqq_sma = get_qqq_data()
        vix = get_vix_data()
        fgi = fetch_fgi()
        pci = fetch_pci()
        usd_krw_rate, usd_krw_change_amount, usd_krw_change_pct = get_usd_krw_rate()
        
        
        try:
            spy_data = yf.Ticker("SPY").history(period="50d")["Close"]
            rsi = calculate_rsi_basic(spy_data)
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
            price_vs_sma = "bullish" if qqq_price > qqq_sma else "bearish"
            trend_text = "상승 추세" if qqq_price > qqq_sma else "하락 추세"
            percentage_diff = ((qqq_price - qqq_sma) / qqq_sma) * 100
            display_metric("🚀 QQQ vs 200일 이동평균", 
                          f"현재: ${qqq_price:.2f} | 200일 평균: ${qqq_sma:.2f} ({percentage_diff:+.1f}%)", 
                          f"{trend_text} - 200일 이동평균 {'위' if qqq_price > qqq_sma else '아래'}", 
                          price_vs_sma)
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

    
    st.markdown("""
    <div class="info-box">
        <h4>📖 지표 설명</h4>
        <ul>
            <li><strong>공포 & 탐욕 지수</strong>: 0-100 범위의 시장 심리 지표 (0=극도공포, 100=극도탐욕)</li>
            <li><strong>VIX</strong>: 시장 변동성 예상 지수 (낮을수록 안정, 높을수록 불안)</li>
            <li><strong>Put/Call 비율</strong>: 풋옵션 대비 콜옵션 거래량 </li>
            <li><strong>RSI</strong>: 상대강도지수 (30 이하 과매도, 70 이상 과매수)</li>
            <li><strong>QQQ vs 200일 이동 평균선</strong>: 나스닥 ETF의 장기 추세 분석</li>
            <li><strong>원달러 환율</strong>: USD/KRW 환율 (상승시 원화약세, 하락시 원화강세)</li>
        </ul>
        <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #6c757d;">
            💡 <strong>팁</strong>: 여러 지표를 종합적으로 해석하여 투자 판단에 활용하세요.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
   
    if auto_refresh:
        import time
        time.sleep(60)
        st.rerun()


def nday_analysis_tab():
    st.markdown('<div class="sub-header">📉 연속 하락 분석기</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <h4>💡 분석 개요</h4>
        <p><strong>하락 분석</strong>: a일 동안 b% 이상 하락한 경우, 마지막 하락일 기준 c일 후 주가 방향을 분석합니다.</p>
        <ul>
            <li><strong>분석기간</strong>: 몇일 동안의 하락을 확인할지 설정</li>
            <li><strong>하락기준</strong>: 해당 기간 동안 총 몇 % 이상 하락했는지 기준</li>
            <li><strong>~일 후 주가</strong>: 하락 마지막일 기준 며칠 후를 분석할지 설정</li>
        </ul>
        <p><strong>예시</strong>: 3일 동안 총 10% 하락 → 마지막일 기준 5일 후 주가가 회복되었나?</p>
        <p><strong>해외 주식</strong>: 티커로 검색 &nbsp;&nbsp;&nbsp;&nbsp; <strong>국내 주식</strong>: 종목명 검색이 안될시 종목 코드 입력</p>
        
    </div>
    """, unsafe_allow_html=True)
    
    
    col1, col2, col3, col4, col5 = st.columns([1.2, 1, 1, 1, 1])
    
    with col1:
        ticker_input = st.text_input("📊 종목 입력", 
                                   value="QQQ", 
                                   help="예: QQQ, SPY, AAPL, 삼성전자, 005930 등")
    
    with col2:
        analysis_days = st.number_input("📅 분석기간 (일)", 
                                      min_value=1, max_value=30, 
                                      value=1, step=1,
                                      help="연속 며칠 동안의 하락을 분석할지")
    

    with col3:
        drop_threshold = st.number_input("📉 하락기준 (%)", 
                                  min_value=1.0, max_value=99.0, 
                                  value=5.0, step=0.5,
                                  help="분석기간 동안 총 이만큼 하락한 경우")
    

    with col4:
        day_options = {
            "1일": 1,
            "3일": 3,
            "5일": 5,
            "1주(7일)": 7,
            "2주(14일)": 14,
            "1개월(30일)": 30,
            "3개월(90일)": 90,
            "6개월(180일)": 180,
            "1년(365일)": 365
        }
        
        selected_label = st.selectbox(
            "📈 ~일 후 주가", 
            options=list(day_options.keys()),
            index=1,  
            help="하락 마지막일로부터 며칠 후를 분석할지 선택"
        )
        
        
        days_after = day_options[selected_label]
    
    with col5:
        start_date = st.date_input("📅 분석 시작일", 
                                 value=pd.to_datetime("2020-01-01"),
                                 min_value=pd.to_datetime("1990-01-01"),
                                 max_value=pd.to_datetime("today"),
                                 help="이 날짜부터 현재까지 분석")
    
    
    processed_ticker, company_name = process_ticker_input(ticker_input)
    
    if company_name:
        st.info(f"🇰🇷 한국 주식: **{company_name}** ({processed_ticker}) 분석 준비")
    elif processed_ticker != ticker_input.upper():
        st.info(f"🌏 해외 주식: **{processed_ticker}** 분석 준비")
    
    if st.button("🔍 분석 실행", type="primary", use_container_width=True):
        with st.spinner("데이터를 불러오고 분석 중... 잠시만 기다려주세요."):
            try:
                
                data = yf.download(processed_ticker, start=start_date)
                
                if data.empty:
                    st.error(f"❌ {processed_ticker} 데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
                    
                    
                    if processed_ticker.endswith(".KS"):
                        st.info("""
                        💡 **한국 주식 입력 방법**:
                        - 회사명 입력: "삼성전자", "SK하이닉스" 등
                        - 6자리 숫자 코드: "005930", "000660" 등
                        - 전체 티커: "005930.KS", "000660.KS" 등
                        """)
                    return
                
               
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.droplevel(1)
                
                data = data[['Close']].copy()
                
                
                signal_periods = find_consecutive_drop_periods(data, analysis_days, drop_threshold)
                
                if len(signal_periods) == 0:
                    st.warning(f"⚠️ {analysis_days}일 동안 {drop_threshold}% 이상 하락한 기간이 없습니다. 기준을 조정해보세요.")
                    return
                
                
                signal_df = pd.DataFrame(signal_periods)
                signal_df.set_index('end_date', inplace=True)
                
                
                signal_df = add_nday_later_prices(signal_df, data, days_after)
                
                
                signal_df = signal_df.dropna(subset=[f'Price_{days_after}D_Later'])
                
                
                if len(signal_df) > 0:
                    avg_actual_days = signal_df['Actual_Days_Later'].mean()
                    st.info(f"📅 목표: {days_after}일 후 → 실제 평균: {avg_actual_days:.1f}일 후 데이터 사용 (주말/공휴일로 인한 차이)")
                
                if len(signal_df) == 0:
                    st.warning(f"⚠️ {days_after}일 후 데이터가 있는 하락 기간이 없습니다. 기간을 조정해보세요.")
                    return
                
                
                signal_df['Result'] = signal_df.apply(
                    lambda row: 'Win' if row['end_price'] < row[f'Price_{days_after}D_Later'] else 'Lose',
                    axis=1
                )
                
                
                signal_df[f'Price_Change_{days_after}D'] = (
                    (signal_df[f'Price_{days_after}D_Later'] - signal_df['end_price']) / signal_df['end_price'] * 100
                )
                
                
                counts = signal_df['Result'].value_counts()
                total_signals = len(signal_df)
                win_count = counts.get('Win', 0)  
                lose_count = counts.get('Lose', 0)  
                winrate = (win_count / total_signals) if total_signals > 0 else 0
                rate = winrate * 100
                
                
                display_ticker = f"{company_name} ({processed_ticker})" if company_name else processed_ticker
                st.success(f"✅ **{display_ticker}** 분석 완료! {total_signals}개의 하락을 분석했습니다.")
                
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 총 신호", f"{total_signals}회")
                
                with col2:
                    avg_drop = signal_df['total_drop_pct'].mean()
                    st.metric(f"📉 평균 {analysis_days}일 하락률", f"{avg_drop:.2f}%")
                    
                with col3:
                    max_drop = signal_df['total_drop_pct'].max()
                    st.metric(f"📉 최대 {analysis_days}일 하락률", f"{max_drop:.2f}%")
                    
                with col4:
                    avg_nd_change = signal_df[f'Price_Change_{days_after}D'].mean()
                    st.metric(f"🔄 평균 {days_after}일 변화", f"{avg_nd_change:+.2f}%")
                
                st.markdown("---")
                
                
                st.subheader(f"🎯 {analysis_days}일 동안{drop_threshold}% 하락 후 {days_after}일 뒤 주가 분석")
                
                result_cols = st.columns(2)
                
                with result_cols[0]:
                    win_percentage = (win_count / total_signals) * 100
                    st.markdown(f"""
                    <div class="result-box lose-box">
                        <h3>🟢 상승 (회복)</h3>
                        <h1>{win_count}회 ({win_percentage:.1f}%)</h1>
                        <p>{analysis_days}일 동안{drop_threshold}% 하락 후 {days_after}일 뒤 주가가 회복된 경우</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with result_cols[1]:
                    lose_percentage = (lose_count / total_signals) * 100
                    st.markdown(f"""
                    <div class="result-box win-box">
                        <h3>🔴 추가 하락</h3>
                        <h1>{lose_count}회 ({lose_percentage:.1f}%)</h1>
                        <p>{analysis_days}일 동안{drop_threshold}% 하락 후 {days_after}일 뒤에도 추가 하락한 경우</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                
                st.markdown("---")
                st.subheader("💰 투자 전략 제안")
                
                ticker_display = company_name if company_name else processed_ticker
                
                if winrate > 0.6:
                    strategy_color = "lose-box"
                    strategy_text = f"""
                    <h4>📈 회복 대기 전략 추천</h4>
                    <p><strong>{rate:.1f}%</strong>의 확률로 {days_after}일 후 주가가 회복되었습니다.</p>
                    <p>💡 <strong>추천</strong>: {ticker_display}가 {analysis_days}일 동안 {drop_threshold}% 하락해도 {days_after}일 정도는 기다려보세요.</p>
                    """
                elif winrate < 0.4:
                    strategy_color = "win-box"
                    strategy_text = f"""
                    <h4>📉 손절 전략 추천</h4>
                    <p><strong>{(100-rate):.1f}%</strong>의 확률로 {days_after}일 후에도 추가 하락했습니다.</p>
                    <p>💡 <strong>추천</strong>: {ticker_display}가 {analysis_days}일 동안 {drop_threshold}% 하락하면 빠른 손절을 고려하세요.</p>
                    """
                else:
                    strategy_color = "result-box"
                    strategy_text = f"""
                    <h4>⚖️ 중립적 결과</h4>
                    <p>회복과 추가하락 확률이 비슷합니다 ({rate:.1f}% vs {(100-rate):.1f}%).</p>
                    <p>💡 <strong>추천</strong>: 다른 지표와 함께 종합적으로 판단하세요.</p>
                    """
                
                st.markdown(f'<div class="{strategy_color}">{strategy_text}</div>', unsafe_allow_html=True)
                
                
                if len(signal_df) > 0:
                    st.markdown("---")
                    st.subheader("📅 최근 하락 사례 (최근 50개)")
                    
                    recent_signals = signal_df.tail(50).sort_index(ascending=False).copy()          
                    recent_signals.index = recent_signals.index.strftime('%Y-%m-%d')
                    
                    
                    display_data = recent_signals[['start_date', 'total_drop_pct', 'end_price', f'Price_{days_after}D_Later', f'Price_Change_{days_after}D', 'Result']].copy()
                    display_data['start_date'] = pd.to_datetime(display_data['start_date']).dt.strftime('%Y-%m-%d')
                    
                    
                    if company_name:
                        display_data.columns = ['시작일', f'{analysis_days}일하락률(%)', '마지막일종가(₩)', f'{days_after}일후종가(₩)', f'{days_after}일간변화(%)', '결과']
                        
                        display_data['마지막일종가(₩)'] = display_data['마지막일종가(₩)'].round(0).astype(int)
                        display_data[f'{days_after}일후종가(₩)'] = display_data[f'{days_after}일후종가(₩)'].round(0).astype(int)
                        display_data[f'{analysis_days}일하락률(%)'] = display_data[f'{analysis_days}일하락률(%)'].round(2)
                        display_data[f'{days_after}일간변화(%)'] = display_data[f'{days_after}일간변화(%)'].round(2)
                    else:
                        display_data.columns = ['시작일', f'{analysis_days}일하락률(%)', '마지막일종가($)', f'{days_after}일후종가($)', f'{days_after}일간변화(%)', '결과']
                        display_data = display_data.round(2)

                    display_data['결과'] = display_data['결과'].map({
                        'Win': f'{days_after}일 후 📈',
                        'Lose': f'{days_after}일 후 📉'
                    })
                    
                    
                    def color_result(val):
                        if val == f'{days_after}일 후 📈':
                            return 'background-color: #d4edda; color: #155724'
                        elif val == f'{days_after}일 후 📉':
                            return 'background-color: #f8d7da; color: #721c24'
                        return ''
                    
                    def color_change(val):
                        if val > 0:
                            return 'color: #28a745; font-weight: bold'
                        elif val < 0:
                            return 'color: #dc3545; font-weight: bold'
                        return ''

                    styled_df = display_data.style.applymap(color_result, subset=['결과']) \
                                                  .applymap(color_change, subset=[f'{days_after}일간변화(%)'])
                    
                    st.dataframe(styled_df, use_container_width=True)
                        
                
                st.markdown("---")
                st.subheader("📈 상세 통계")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    avg_win_change = signal_df[signal_df['Result'] == 'Win'][f'Price_Change_{days_after}D'].mean()
                    st.metric(f"회복 시 평균 {days_after}일 변화", f"{avg_win_change:+.2f}%" if not pd.isna(avg_win_change) else "N/A")
                
                with col2:
                    avg_lose_change = signal_df[signal_df['Result'] == 'Lose'][f'Price_Change_{days_after}D'].mean()
                    st.metric(f"추가하락 시 평균 {days_after}일 변화", f"{avg_lose_change:+.2f}%" if not pd.isna(avg_lose_change) else "N/A")
                
                with col3:
                    median_change = signal_df[f'Price_Change_{days_after}D'].median()
                    st.metric(f"{days_after}일 변화 중간값", f"{median_change:+.2f}%")
                
                
                st.markdown(f"""
                <div class="info-box">
                    <h4>⚠️ 주의사항</h4>
                    <ul>
                        <li>이 분석은 과거 <strong>{analysis_days}일  하락</strong> 패턴을 바탕으로 한 통계적 분석입니다.</li>
                        <li>실제 투자 결정시에는 다른 기술적/기본적 분석과 함께 고려하세요.</li>
                        <li>시장 상황에 따라 과거 패턴이 반복되지 않을 수 있습니다.</li>
                    </ul>
                    <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #6c757d;">
                        💡 <strong>권장</strong>: 이 분석 결과를 다른 투자 지표와 함께 종합적으로 활용하세요.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
                st.info("💡 다른 티커를 시도하거나 날짜 범위를 조정해보세요.")
                
                
                if processed_ticker.endswith(".KS"):
                    st.warning("""
                    🇰🇷 **한국 주식 관련 팁**:
                    - 일부 한국 주식은 yfinance에서 데이터가 제한적일 수 있습니다.
                    - 상장 폐지되었거나 최근 상장한 종목은 데이터가 없을 수 있습니다.
                    - 분석 시작일을 더 최근으로 설정해보세요.
                    """)


def sp500_screener_tab():
    st.markdown('<div class="sub-header">🎯 S&P500 RSI 검색기</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <h4>💡 스크리닝 조건</h4>
        <p><strong>과매도 + 변동성 낮음 조건</strong>으로 반등 후보 종목을 찾습니다.</p>
        <ul>
            <li><strong>RSI < 40</strong>: 과매도 상태 (상대강도지수 40 미만)</li>
            <li><strong>볼린저 밴드 하단</strong>: BB Position < 0.5 (하단 근처에 위치)</li>
            <li><strong>볼린저 밴드 폭 축소</strong>: 현재 BB Width < 52주 평균 (변동성 낮음)</li>
        </ul>
        <p><strong>투자 아이디어</strong>: 과매도 + 낮은 변동성 = 반등 가능성이 높은 종목</p>
    </div>
    """, unsafe_allow_html=True)
    

    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        rsi_threshold = st.slider("RSI 기준값", 25, 60, 40, 1, help="이 값 미만인 종목만 표시")
    
    with col2:
        bb_position_threshold = st.slider("BB Position 기준", 0.1, 0.8, 0.5, 0.05, help="이 값 미만인 종목만 표시 (0=하단, 1=상단)")
    
    with col3:
        max_stocks = st.selectbox("최대 표시 종목 수", [10, 30, 50, 100], index=2, help="조건을 만족하는 상위 몇 개 종목을 표시할지")
    
    if st.button("🔍 S&P500 스크리닝 실행", type="primary", use_container_width=True):
        
     
        progress_bar = st.progress(0)
        status_text = st.empty()
        
   
        sp500_tickers = get_sp500_tickers()
        status_text.text(f"📈 S&P 500 종목 {len(sp500_tickers)}개 분석 시작...")
        
        qualifying_stocks = []
        
       
        with ThreadPoolExecutor(max_workers=10) as executor:
        
            future_to_ticker = {executor.submit(analyze_stock, ticker): ticker for ticker in sp500_tickers}
            
            completed = 0
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                completed += 1
                
             
                progress = completed / len(sp500_tickers)
                progress_bar.progress(progress)
                status_text.text(f"📊 분석 중... {completed}/{len(sp500_tickers)} ({progress*100:.1f}%) - 현재: {ticker}")
                
                try:
                    result = future.result()
                    if result and result['meets_criteria']:
                  
                        if (result['rsi'] < rsi_threshold and 
                            result['bb_position'] < bb_position_threshold):
                            qualifying_stocks.append(result)
                            
                        
                            if len(qualifying_stocks) <= 5:  # 처음 5개만 실시간 표시
                                st.success(f"✅ 조건 만족: **{ticker}** (RSI: {result['rsi']:.1f}, BB Pos: {result['bb_position']:.3f})")
                
                except Exception as e:
                    continue
        
        progress_bar.progress(1.0)
        status_text.text("✅ 분석 완료!")
        
        
        if qualifying_stocks:
          
            qualifying_stocks.sort(key=lambda x: x['rsi'])
            
          
            qualifying_stocks = qualifying_stocks[:max_stocks]
            
            st.success(f"🎯 **{len(qualifying_stocks)}개 종목**이 조건을 만족합니다!")
            
        
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_rsi = np.mean([stock['rsi'] for stock in qualifying_stocks])
                st.metric("평균 RSI", f"{avg_rsi:.1f}")
            
            with col2:
                avg_bb_pos = np.mean([stock['bb_position'] for stock in qualifying_stocks])
                st.metric("평균 BB Position", f"{avg_bb_pos:.3f}")
            
            with col3:
                lowest_rsi_stock = min(qualifying_stocks, key=lambda x: x['rsi'])
                st.metric("최저 RSI", f"{lowest_rsi_stock['rsi']:.1f} ({lowest_rsi_stock['ticker']})")
            
            with col4:
                lowest_bb_stock = min(qualifying_stocks, key=lambda x: x['bb_position'])
                st.metric("최저 BB Position", f"{lowest_bb_stock['bb_position']:.3f} ({lowest_bb_stock['ticker']})")
            
            st.markdown("---")
            
         
            st.subheader(f"📋 조건 만족 종목 상세 ({len(qualifying_stocks)}개)")
            
        
            results_data = []
            for i, stock in enumerate(qualifying_stocks, 1):
           
                stock_info = get_stock_info(stock['ticker'])
                
                results_data.append({
                    '순위': i,
                    '티커': stock['ticker'],
                    '회사명': stock_info['name'],
                    '섹터': stock_info['sector'],
                    '현재가($)': f"{stock['price']:.2f}",
                    'RSI': f"{stock['rsi']:.1f}",
                    'BB Position': f"{stock['bb_position']:.3f}",
                    'BB Width': f"{stock['bb_width']:.4f}",
                    'BB Width (52주평균)': f"{stock['bb_width_52w_avg']:.4f}",
                    '상단밴드($)': f"{stock['upper_band']:.2f}",
                    '하단밴드($)': f"{stock['lower_band']:.2f}",
                    '20일이평($)': f"{stock['sma']:.2f}"
                })
            
            results_df = pd.DataFrame(results_data)
            
         
            def highlight_good_rsi(val):
                try:
                    num_val = float(val)
                    if num_val < 25:
                        return 'background-color: #dc3545; font-weight: bold'  
                    elif num_val < 30:
                        return 'background-color: #fd7e14; font-weight: bold' 
                    elif num_val < 35:
                        return 'background-color: #198754'  
                except:
                    pass
                return ''
            
            def highlight_bb_position(val):
                try:
                    num_val = float(val)
                    if num_val < 0.2:
                        return 'background-color: #dc3545; font-weight: bold'  
                    elif num_val < 0.35:
                        return 'background-color: #fd7e14; font-weight: bold'  
                    elif num_val < 0.5:
                        return 'background-color: #198754'  
                except:
                    pass
                return ''
            
           
            styled_df = results_df.style.applymap(highlight_good_rsi, subset=['RSI']) \
                                       .applymap(highlight_bb_position, subset=['BB Position'])
            
            st.dataframe(styled_df, use_container_width=True, height=600)
            
            
            st.markdown("---")
            st.subheader("⭐ 주목할 만한 종목들")
            
           
            for i, stock in enumerate(qualifying_stocks[:3], 1):
                stock_info = get_stock_info(stock['ticker'])
                
                st.markdown(f"""
                <div class="stock-highlight">
                    <h4>#{i} {stock['ticker']} - {stock_info['name']}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 10px;">
                        <div><strong>💰 현재가:</strong> ${stock['price']:.2f}</div>
                        <div><strong>📊 RSI:</strong> {stock['rsi']:.1f}</div>
                        <div><strong>🎯 BB Position:</strong> {stock['bb_position']:.3f}</div>
                        <div><strong>📏 BB Width:</strong> {stock['bb_width']:.4f}</div>
                        <div><strong>🏢 섹터:</strong> {stock_info['sector']}</div>
                    </div>
                    <p style="margin-top: 8px; color: #666; font-size: 0.9rem;">
                        하단밴드: ${stock['lower_band']:.2f} | 20일평균: ${stock['sma']:.2f} | 상단밴드: ${stock['upper_band']:.2f}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            
            st.markdown("---")
            st.subheader("💡 투자 전략 제안")
            
            avg_rsi = np.mean([stock['rsi'] for stock in qualifying_stocks])
            avg_bb_pos = np.mean([stock['bb_position'] for stock in qualifying_stocks])
            
            if avg_rsi < 30 and avg_bb_pos < 0.3:
                strategy_color = "lose-box"
                strategy_title = "🟢 강력한 매수 신호"
                strategy_text = f"""
                <p>발견된 종목들의 평균 RSI({avg_rsi:.1f})와 BB Position({avg_bb_pos:.3f})이 모두 매우 낮습니다.</p>
                <p>💡 <strong>전략</strong>: 단계적 매수를 통해 리스크를 분산하고, 반등 시점을 노려보세요.</p>
                """
            elif avg_rsi < 35 and avg_bb_pos < 0.4:
                strategy_color = "result-box"
                strategy_title = "🟡 매수 고려 신호"
                strategy_text = f"""
                <p>발견된 종목들이 과매도 상태에 근접해 있습니다 (평균 RSI: {avg_rsi:.1f}, BB Position: {avg_bb_pos:.3f}).</p>
                <p>💡 <strong>전략</strong>: 추가적인 기본 분석과 함께 신중한 매수를 고려해보세요.</p>
                """
            else:
                strategy_color = "metric-container"
                strategy_title = "⚖️ 신중한 접근"
                strategy_text = f"""
                <p>조건을 만족하지만 극도의 과매도는 아닙니다 (평균 RSI: {avg_rsi:.1f}).</p>
                <p>💡 <strong>전략</strong>: 시장 상황과 개별 종목 펀더멘털을 종합적으로 검토하세요.</p>
                """
            
            st.markdown(f"""
            <div class="{strategy_color}">
                <h4>{strategy_title}</h4>
                {strategy_text}
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.warning(f"""
            ⚠️ 현재 설정한 조건을 만족하는 S&P 500 종목이 없습니다.
            
            **현재 조건:**
            - RSI < {rsi_threshold}
            - BB Position < {bb_position_threshold}
            - BB Width < 52주 평균
            
            💡 **조건을 완화해보세요:**
            - RSI 기준을 45 정도로 높이기
            - BB Position을 0.6-0.7로 높이기
            """)
        
        # 분석 정보
        st.markdown("---")
        st.markdown("""
        <div class="info-box">
            <h4>📚 지표 해석 가이드</h4>
            <ul>
                <li><strong>RSI (Relative Strength Index)</strong>:
                    <ul>
                        <li>30 미만: 과매도 (매수 고려)</li>
                        <li>25 미만: 극도 과매도 (강력한 매수 신호)</li>
                        <li>70 이상: 과매수 (매도 고려)</li>
                    </ul>
                </li>
                <li><strong>볼린저 밴드 Position</strong>:
                    <ul>
                        <li>0.0: 하단 밴드 (극도 과매도)</li>
                        <li>0.2: 하단 근처 (과매도)</li>
                        <li>0.5: 중간선 (20일 이동평균)</li>
                        <li>0.8: 상단 근처 (과매수)</li>
                        <li>1.0: 상단 밴드 (극도 과매수)</li>
                    </ul>
                </li>
                <li><strong>볼린저 밴드 Width</strong>:
                    <ul>
                        <li>52주 평균 대비 낮음: 변동성 축소 (돌파 준비)</li>
                        <li>52주 평균 대비 높음: 변동성 확대 (추세 진행 중)</li>
                    </ul>
                </li>
            </ul>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: #6c757d;">
                ⚠️ <strong>주의</strong>: 이 분석은 기술적 지표만을 고려합니다. 실제 투자 시에는 기본 분석, 시장 상황, 뉴스 등을 종합적으로 고려하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)


def main():
    st.markdown('<h1 class="main-header">📈 주식 시장 분석 대시보드</h1>', unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 시장 감정", "📉 하락 분석", "🎯 S&P500 스크리너"])
    
    with tab1:
        market_sentiment_tab()
    
    with tab2:
        nday_analysis_tab()
    
    with tab3:
        sp500_screener_tab()
    
    
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



