import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from stock_library import (
        get_sp500_tickers,
        get_sp500_company_name,
    )
except ImportError:
    def get_sp500_tickers():
        return ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN"]
    def get_sp500_company_name(ticker):
        return "Unknown"


# ── 분석 헬퍼 ────────────────────────────────────────────────────────

def calculate_rsi(prices, window=14):
    if len(prices) < window + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    delta    = prices.diff()
    gain     = delta.where(delta > 0, 0)
    loss     = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    for i in range(window, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (window-1) + gain.iloc[i]) / window
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (window-1) + loss.iloc[i]) / window
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(prices, window=20, num_std=2):
    sma         = prices.rolling(window=window).mean()
    std         = prices.rolling(window=window).std()
    upper_band  = sma + (std * num_std)
    lower_band  = sma - (std * num_std)
    bb_position = (prices - lower_band) / (upper_band - lower_band)
    bb_width    = (upper_band - lower_band) / sma
    return bb_position, bb_width, upper_band, lower_band, sma

def analyze_stock(ticker):
    try:
        stock  = yf.Ticker(ticker)
        hist   = stock.history(period="2y")
        if hist.empty or len(hist) < 252:
            return None
        prices = hist['Close']

        rsi              = calculate_rsi(prices)
        current_rsi      = rsi.iloc[-1] if len(rsi) > 0 else None
        bb_position, bb_width, upper_band, lower_band, sma = calculate_bollinger_bands(prices)
        current_bb_pos   = bb_position.iloc[-1] if len(bb_position) > 0 else None
        current_bb_width = bb_width.iloc[-1]     if len(bb_width) > 0    else None
        bb_width_52w_avg = bb_width.rolling(252).mean().iloc[-1] if len(bb_width) >= 252 else None
        current_price    = prices.iloc[-1]
        current_upper    = upper_band.iloc[-1]   if len(upper_band) > 0  else None
        current_lower    = lower_band.iloc[-1]   if len(lower_band) > 0  else None
        current_sma      = sma.iloc[-1]          if len(sma) > 0         else None

        if (current_rsi is not None and current_bb_pos is not None
                and current_bb_width is not None and bb_width_52w_avg is not None):
            if (current_rsi < 40 and current_bb_pos < 0.5 and current_bb_width < bb_width_52w_avg):
                return {
                    'ticker':           ticker,
                    'price':            current_price,
                    'rsi':              current_rsi,
                    'bb_position':      current_bb_pos,
                    'bb_width':         current_bb_width,
                    'bb_width_52w_avg': bb_width_52w_avg,
                    'upper_band':       current_upper,
                    'lower_band':       current_lower,
                    'sma':              current_sma,
                    'meets_criteria':   True,
                }
        return None
    except Exception:
        return None

def get_stock_info(ticker):
    try:
        local_name = get_sp500_company_name(ticker)
        stock      = yf.Ticker(ticker)
        info       = stock.info
        return {
            'name':       local_name if local_name != "Unknown" else info.get('shortName', ticker),
            'sector':     info.get('sector', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
        }
    except:
        return {'name': ticker, 'sector': 'N/A', 'market_cap': 'N/A'}


# ── 탭 메인 함수 ─────────────────────────────────────────────────────

def sp500_screener_tab():
    st.markdown('''
    <div class="sub-header" style="color: inherit;">
        🎯 S&P500 RSI 검색기
    </div>
    ''', unsafe_allow_html=True)
    

    with st.expander("💡 설명 ", expanded=False):
        st.markdown("""
        <div class="info-box">
            <h4>💡 스크리닝 조건</h4>
            <p><strong>과매도 + 변동성 낮음 조건</strong>으로 반등 후보 종목을 찾습니다.</p>
            <ul>
                <li><strong>RSI &lt; 40</strong>: 과매도 상태 (상대강도지수 40 미만)</li>
                <li><strong>볼린저 밴드 하단</strong>: BB Position &lt; 0.5 (하단 근처에 위치)</li>
                <li><strong>볼린저 밴드 폭 축소</strong>: 현재 BB Width &lt; 52주 평균 (변동성 낮음)</li>
            </ul>
            <p><strong>투자 아이디어</strong>: 과매도 + 낮은 변동성 = 반등 가능성이 높은 종목</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        rsi_threshold = st.slider("RSI 기준값", 25, 60, 40, 1, help="이 값 미만인 종목만 표시")
    with col2:
        bb_position_threshold = st.slider("BB Position 기준", 0.1, 0.8, 0.5, 0.05,
                                          help="이 값 미만인 종목만 표시 (0=하단, 1=상단)")
    with col3:
        max_stocks = st.selectbox("최대 표시 종목 수", [10, 30, 50, 100], index=2,
                                  help="조건을 만족하는 상위 몇 개 종목을 표시할지")

    if st.button("🔍 S&P500 스크리닝 실행", type="primary", use_container_width=True):
        progress_bar      = st.progress(0)
        status_text       = st.empty()
        sp500_tickers     = get_sp500_tickers()
        status_text.text(f"📈 S&P 500 종목 {len(sp500_tickers)}개 분석 시작...")
        qualifying_stocks = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(analyze_stock, t): t for t in sp500_tickers}
            completed = 0
            for future in as_completed(future_to_ticker):
                ticker    = future_to_ticker[future]
                completed += 1
                progress  = completed / len(sp500_tickers)
                progress_bar.progress(progress)
                status_text.text(f"📊 분석 중... {completed}/{len(sp500_tickers)} ({progress*100:.1f}%) - 현재: {ticker}")
                try:
                    result = future.result()
                    if result and result['meets_criteria']:
                        if (result['rsi'] < rsi_threshold and result['bb_position'] < bb_position_threshold):
                            qualifying_stocks.append(result)
                            if len(qualifying_stocks) <= 5:
                                st.success(f"✅ 조건 만족: **{ticker}** (RSI: {result['rsi']:.1f}, BB Pos: {result['bb_position']:.3f})")
                except Exception:
                    continue

        progress_bar.progress(1.0)
        status_text.text("✅ 분석 완료!")

        if qualifying_stocks:
            qualifying_stocks.sort(key=lambda x: x['rsi'])
            qualifying_stocks = qualifying_stocks[:max_stocks]
            st.success(f"🎯 **{len(qualifying_stocks)}개 종목**이 조건을 만족합니다!")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_rsi = np.mean([s['rsi'] for s in qualifying_stocks])
                st.metric("평균 RSI", f"{avg_rsi:.1f}")
            with col2:
                avg_bb_pos = np.mean([s['bb_position'] for s in qualifying_stocks])
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
                    '순위':              i,
                    '티커':              stock['ticker'],
                    '회사명':            stock_info['name'],
                    '섹터':              stock_info['sector'],
                    '현재가($)':         f"{stock['price']:.2f}",
                    'RSI':               f"{stock['rsi']:.1f}",
                    'BB Position':       f"{stock['bb_position']:.3f}",
                    'BB Width':          f"{stock['bb_width']:.4f}",
                    'BB Width (52주평균)': f"{stock['bb_width_52w_avg']:.4f}",
                    '상단밴드($)':       f"{stock['upper_band']:.2f}",
                    '하단밴드($)':       f"{stock['lower_band']:.2f}",
                    '20일이평($)':       f"{stock['sma']:.2f}",
                })

            results_df = pd.DataFrame(results_data)

            def highlight_good_rsi(val):
                try:
                    v = float(val)
                    if v < 25:   return 'background-color: #dc3545; font-weight: bold'
                    elif v < 30: return 'background-color: #fd7e14; font-weight: bold'
                    elif v < 35: return 'background-color: #198754'
                except: pass
                return ''

            def highlight_bb_position(val):
                try:
                    v = float(val)
                    if v < 0.2:   return 'background-color: #dc3545; font-weight: bold'
                    elif v < 0.35: return 'background-color: #fd7e14; font-weight: bold'
                    elif v < 0.5:  return 'background-color: #198754'
                except: pass
                return ''

            # ✅ 수정된 부분: applymap → map
            styled_df = results_df.style \
                .map(highlight_good_rsi,    subset=['RSI']) \
                .map(highlight_bb_position, subset=['BB Position'])
            st.dataframe(styled_df, use_container_width=True, height=600)

            st.markdown("---")
            st.subheader("⭐ 주목할 만한 종목들")
            for i, stock in enumerate(qualifying_stocks[:3], 1):
                stock_info = get_stock_info(stock['ticker'])
                st.markdown(f"""
                <div class="stock-highlight" style="color: inherit;">
                    <h4 style="color: inherit;">#{i} {stock['ticker']} - {stock_info['name']}</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 10px; color: inherit;">
                        <div><strong>💰 현재가:</strong> ${stock['price']:.2f}</div>
                        <div><strong>📊 RSI:</strong> {stock['rsi']:.1f}</div>
                        <div><strong>🎯 BB Position:</strong> {stock['bb_position']:.3f}</div>
                        <div><strong>📏 BB Width:</strong> {stock['bb_width']:.4f}</div>
                        <div><strong>🏢 섹터:</strong> {stock_info['sector']}</div>
                    </div>
                    <p style="margin-top: 8px; color: inherit; opacity: 0.7; font-size: 0.9rem;">
                        하단밴드: ${stock['lower_band']:.2f} | 20일평균: ${stock['sma']:.2f} | 상단밴드: ${stock['upper_band']:.2f}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("💡 투자 전략 제안")
            avg_rsi    = np.mean([s['rsi']         for s in qualifying_stocks])
            avg_bb_pos = np.mean([s['bb_position'] for s in qualifying_stocks])

            if avg_rsi < 30 and avg_bb_pos < 0.3:
                sc, st_title = "lose-box", "🟢 강력한 매수 신호"
                st_text = f"<p style='color: inherit;'>평균 RSI({avg_rsi:.1f})와 BB Position({avg_bb_pos:.3f})이 모두 매우 낮습니다.</p><p style='color: inherit;'>💡 <strong>전략</strong>: 단계적 매수를 통해 리스크를 분산하고, 반등 시점을 노려보세요.</p>"
            elif avg_rsi < 35 and avg_bb_pos < 0.4:
                sc, st_title = "result-box", "🟡 매수 고려 신호"
                st_text = f"<p style='color: inherit;'>과매도 상태에 근접해 있습니다 (평균 RSI: {avg_rsi:.1f}, BB Position: {avg_bb_pos:.3f}).</p><p style='color: inherit;'>💡 <strong>전략</strong>: 추가적인 기본 분석과 함께 신중한 매수를 고려해보세요.</p>"
            else:
                sc, st_title = "metric-container", "⚖️ 신중한 접근"
                st_text = f"<p style='color: inherit;'>조건을 만족하지만 극도의 과매도는 아닙니다 (평균 RSI: {avg_rsi:.1f}).</p><p style='color: inherit;'>💡 <strong>전략</strong>: 시장 상황과 개별 종목 펀더멘털을 종합적으로 검토하세요.</p>"

            st.markdown(f'<div class="{sc}" style="color: inherit;"><h4 style="color: inherit;">{st_title}</h4>{st_text}</div>', unsafe_allow_html=True)

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
                        <li>0.5: 중간선 (20일 이동평균)</li>
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
            <p style="margin-top: 0
