import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

try:
    from stock_library import process_ticker_input
except ImportError:
    def process_ticker_input(ticker):
        return ticker.upper(), None


# ── 헬퍼 함수 ────────────────────────────────────────────────────────

def get_trading_day_after(data_index, target_date, days_after):
    try:
        target_calendar_date = target_date + pd.Timedelta(days=days_after)
        future_dates = data_index[data_index >= target_calendar_date]
        return future_dates[0] if len(future_dates) > 0 else None
    except (KeyError, IndexError):
        return None

def add_nday_later_prices(signal_days, data, days_after):
    nday_later_prices = []
    actual_days_list = []
    for signal_date in signal_days.index:
        future_date = get_trading_day_after(data.index, signal_date, days_after)
        if future_date is not None and future_date in data.index:
            nday_later_prices.append(data.loc[future_date, 'Close'])
            actual_days_list.append((future_date - signal_date).days)
        else:
            nday_later_prices.append(None)
            actual_days_list.append(None)
    signal_days[f'Price_{days_after}D_Later'] = nday_later_prices
    signal_days['Actual_Days_Later'] = actual_days_list
    return signal_days

def find_consecutive_drop_periods(data, analysis_days, drop_threshold):
    signal_periods = []
    for i in range(analysis_days, len(data)):
        start_price = data.iloc[i - analysis_days]['Close']
        end_price   = data.iloc[i]['Close']
        total_drop  = ((start_price - end_price) / start_price) * 100
        if total_drop >= drop_threshold:
            signal_periods.append({
                'start_date':     data.iloc[i - analysis_days].name,
                'end_date':       data.iloc[i].name,
                'start_price':    start_price,
                'end_price':      end_price,
                'total_drop_pct': total_drop,
                'analysis_days':  analysis_days,
            })
    return signal_periods


# ── 탭 메인 함수 ─────────────────────────────────────────────────────

def nday_analysis_tab():
    st.markdown('<div class="sub-header">📉 연속 하락 분석기</div>', unsafe_allow_html=True)

    with st.expander("💡 설명", expanded=False):
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
        ticker_input = st.text_input("📊 종목 입력", value="QQQ",
                                     help="예: QQQ, SPY, AAPL, 삼성전자, 005930 등")
    with col2:
        analysis_days = st.number_input("📅 분석기간 (일)", min_value=1, max_value=30,
                                        value=1, step=1, help="연속 며칠 동안의 하락을 분석할지")
    with col3:
        drop_threshold = st.number_input("📉 하락기준 (%)", min_value=1.0, max_value=99.0,
                                         value=5.0, step=0.5, help="분석기간 동안 총 이만큼 하락한 경우")
    with col4:
        day_options = {
            "1일": 1, "3일": 3, "5일": 5, "1주(7일)": 7,
            "2주(14일)": 14, "1개월(30일)": 30, "3개월(90일)": 90,
            "6개월(180일)": 180, "1년(365일)": 365,
        }
        selected_label = st.selectbox("📈 ~일 후 주가", options=list(day_options.keys()),
                                      index=1, help="하락 마지막일로부터 며칠 후를 분석할지 선택")
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
                    lambda row: 'Win' if row['end_price'] < row[f'Price_{days_after}D_Later'] else 'Lose', axis=1)
                signal_df[f'Price_Change_{days_after}D'] = (
                    (signal_df[f'Price_{days_after}D_Later'] - signal_df['end_price']) / signal_df['end_price'] * 100)

                counts       = signal_df['Result'].value_counts()
                total_signals = len(signal_df)
                win_count    = counts.get('Win', 0)
                lose_count   = counts.get('Lose', 0)
                winrate      = (win_count / total_signals) if total_signals > 0 else 0
                rate         = winrate * 100

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
                st.subheader(f"🎯 {analysis_days}일 동안 {drop_threshold}% 하락 후 {days_after}일 뒤 주가 분석")

                result_cols = st.columns(2)
                with result_cols[0]:
                    win_pct = (win_count / total_signals) * 100
                    st.markdown(f"""
                    <div class="result-box lose-box">
                        <h3>🟢 상승 (회복)</h3>
                        <h1>{win_count}회 ({win_pct:.1f}%)</h1>
                        <p>{analysis_days}일 동안 {drop_threshold}% 하락 후 {days_after}일 뒤 주가가 회복된 경우</p>
                    </div>""", unsafe_allow_html=True)
                with result_cols[1]:
                    lose_pct = (lose_count / total_signals) * 100
                    st.markdown(f"""
                    <div class="result-box win-box">
                        <h3>🔴 추가 하락</h3>
                        <h1>{lose_count}회 ({lose_pct:.1f}%)</h1>
                        <p>{analysis_days}일 동안 {drop_threshold}% 하락 후 {days_after}일 뒤에도 추가 하락한 경우</p>
                    </div>""", unsafe_allow_html=True)

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
                    display_data = recent_signals[['start_date', 'total_drop_pct', 'end_price',
                                                   f'Price_{days_after}D_Later', f'Price_Change_{days_after}D', 'Result']].copy()
                    display_data['start_date'] = pd.to_datetime(display_data['start_date']).dt.strftime('%Y-%m-%d')

                    if company_name:
                        display_data.columns = ['시작일', f'{analysis_days}일하락률(%)', '마지막일종가(₩)',
                                                 f'{days_after}일후종가(₩)', f'{days_after}일간변화(%)', '결과']
                        display_data['마지막일종가(₩)'] = display_data['마지막일종가(₩)'].round(0).astype(int)
                        display_data[f'{days_after}일후종가(₩)'] = display_data[f'{days_after}일후종가(₩)'].round(0).astype(int)
                        display_data[f'{analysis_days}일하락률(%)'] = display_data[f'{analysis_days}일하락률(%)'].round(2)
                        display_data[f'{days_after}일간변화(%)'] = display_data[f'{days_after}일간변화(%)'].round(2)
                    else:
                        display_data.columns = ['시작일', f'{analysis_days}일하락률(%)', '마지막일종가($)',
                                                 f'{days_after}일후종가($)', f'{days_after}일간변화(%)', '결과']
                        display_data = display_data.round(2)

                    display_data['결과'] = display_data['결과'].map({
                        'Win':  f'{days_after}일 후 📈',
                        'Lose': f'{days_after}일 후 📉',
                    })

                    def color_result(val):
                        if '📈' in str(val):
                            return 'background-color: #d4edda; color: #155724'
                        elif '📉' in str(val):
                            return 'background-color: #f8d7da; color: #721c24'
                        return ''

                    def color_change(val):
                        if val > 0:   return 'color: #28a745; font-weight: bold'
                        elif val < 0: return 'color: #dc3545; font-weight: bold'
                        return ''

                    styled_df = display_data.style \
                        .applymap(color_result, subset=['결과']) \
                        .applymap(color_change, subset=[f'{days_after}일간변화(%)'])
                    st.dataframe(styled_df, use_container_width=True)

                st.markdown("---")
                st.subheader("📈 상세 통계")
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_win = signal_df[signal_df['Result'] == 'Win'][f'Price_Change_{days_after}D'].mean()
                    st.metric(f"회복 시 평균 {days_after}일 변화", f"{avg_win:+.2f}%" if not pd.isna(avg_win) else "N/A")
                with col2:
                    avg_lose = signal_df[signal_df['Result'] == 'Lose'][f'Price_Change_{days_after}D'].mean()
                    st.metric(f"추가하락 시 평균 {days_after}일 변화", f"{avg_lose:+.2f}%" if not pd.isna(avg_lose) else "N/A")
                with col3:
                    median_change = signal_df[f'Price_Change_{days_after}D'].median()
                    st.metric(f"{days_after}일 변화 중간값", f"{median_change:+.2f}%")

                st.markdown(f"""
                <div class="info-box">
                    <h4>⚠️ 주의사항</h4>
                    <ul>
                        <li>이 분석은 과거 <strong>{analysis_days}일 하락</strong> 패턴을 바탕으로 한 통계적 분석입니다.</li>
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
