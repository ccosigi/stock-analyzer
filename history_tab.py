"""
────────────────────────────────────────────────────
app.py 에 추가할 "📈 히스토리 & 상관관계" 탭 코드
────────────────────────────────────────────────────
사용법:
  1. app.py main() 함수 안의 탭 부분을 아래처럼 수정:

      tab1, tab2, tab3, tab4 = st.tabs([
          "📊 시장 감정",
          "📉 하락 분석",
          "🎯 S&P500 스크리너",
          "📈 히스토리 & 상관관계"   # ← 추가
      ])
      ...
      with tab4:
          history_tab()

  2. 이 파일의 history_tab() 함수를 app.py 상단에 붙여넣기
────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import numpy as np

# ── 데이터 로드 ────────────────────────────────────
HISTORY_CSV = "data/market_indicators.csv"

COLUMN_LABELS = {
    "fgi":               "공포&탐욕 (FGI)",
    "vix":               "VIX",
    "qqq_vs_sma200_pct": "QQQ 이격률 (%)",
    "qqq_daily_return":  "QQQ 일수익률 (%)",
    "put_call_ratio":    "Put/Call 비율",
    "spy_rsi":           "SPY RSI",
    "usd_krw":           "원달러 환율",
    "usd_krw_change_pct":"환율 변화율 (%)",
}

@st.cache_data(ttl=3600)
def load_history() -> pd.DataFrame | None:
    try:
        df = pd.read_csv(HISTORY_CSV, parse_dates=["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None


# ── 메인 탭 함수 ───────────────────────────────────
def history_tab():
    st.markdown('<div class="sub-header">📈 일별 시장 지표 히스토리</div>', unsafe_allow_html=True)

    df = load_history()

    if df is None or df.empty:
        st.warning("""
        📭 아직 수집된 데이터가 없습니다.

        **GitHub Actions 설정 확인:**
        1. `.github/workflows/collect_daily_indicators.yml` 파일이 repo에 있는지 확인
        2. `collect_daily_indicators.py` 파일이 repo 루트에 있는지 확인
        3. Actions 탭에서 워크플로우가 활성화되어 있는지 확인
        4. 수동 실행: Actions → `Daily Market Indicators Collector` → `Run workflow`
        """)
        return

    # ── 기간 필터 ──────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        start = st.date_input("시작일", value=min_date, min_value=min_date, max_value=max_date)
    with col_f2:
        end = st.date_input("종료일", value=max_date, min_value=min_date, max_value=max_date)

    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    filtered = df[mask].copy()

    if filtered.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return

    st.success(f"📅 {len(filtered)}일치 데이터 표시 중 ({start} ~ {end})")

    # ── 최근값 요약 카드 ────────────────────────────
    st.markdown("---")
    st.subheader("🔢 최근 지표 값")
    latest = filtered.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("😨 공포&탐욕", f"{latest.get('fgi', 'N/A')}/100"),
        ("📈 VIX",      f"{latest.get('vix', 'N/A')}"),
        ("⚖️ Put/Call", f"{latest.get('put_call_ratio', 'N/A')}"),
        ("📊 SPY RSI",  f"{latest.get('spy_rsi', 'N/A')}"),
    ]
    for col, (label, val) in zip([c1, c2, c3, c4], metrics):
        col.metric(label, val)

    c5, c6, c7, c8 = st.columns(4)
    metrics2 = [
        ("🚀 QQQ 이격률",   f"{latest.get('qqq_vs_sma200_pct', 'N/A')}%"),
        ("📉 QQQ 일수익",   f"{latest.get('qqq_daily_return', 'N/A')}%"),
        ("💱 원달러",       f"₩{latest.get('usd_krw', 'N/A')}"),
        ("💱 환율변화",     f"{latest.get('usd_krw_change_pct', 'N/A')}%"),
    ]
    for col, (label, val) in zip([c5, c6, c7, c8], metrics2):
        col.metric(label, val)

    # ── 지표 트렌드 차트 ────────────────────────────
    st.markdown("---")
    st.subheader("📉 지표 트렌드")

    indicator_options = list(COLUMN_LABELS.keys())
    selected = st.multiselect(
        "표시할 지표 선택",
        options=indicator_options,
        default=["fgi", "vix", "spy_rsi"],
        format_func=lambda x: COLUMN_LABELS[x],
    )

    if selected:
        chart_data = filtered.set_index("date")[selected].rename(columns=COLUMN_LABELS)
        st.line_chart(chart_data)
    else:
        st.info("위에서 지표를 하나 이상 선택하세요.")

    # ── 상관관계 분석 ───────────────────────────────
    st.markdown("---")
    st.subheader("🔗 지표 → 나스닥(QQQ) 당일 수익률 상관관계")
    st.markdown("""
    <div class="info-box">
        <h4>💡 분석 목적</h4>
        <p>각 지표 값이 나스닥(QQQ) <strong>당일 수익률</strong>과 얼마나 관련이 있는지 분석합니다.</p>
        <ul>
            <li><strong>양(+)의 상관</strong>: 지표가 높을수록 나스닥도 상승하는 경향</li>
            <li><strong>음(-)의 상관</strong>: 지표가 높을수록 나스닥이 하락하는 경향</li>
            <li>|r| > 0.5: 강한 상관 &nbsp; | &nbsp; |r| 0.3~0.5: 중간 &nbsp; | &nbsp; |r| < 0.3: 약함</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    numeric_cols = [c for c in COLUMN_LABELS.keys() if c != "qqq_daily_return"]
    corr_df = filtered[numeric_cols + ["qqq_daily_return"]].dropna()

    if len(corr_df) < 5:
        st.warning(f"상관관계 계산에 데이터가 부족합니다. (현재 {len(corr_df)}일, 최소 5일 필요)")
    else:
        corr_series = corr_df[numeric_cols].corrwith(corr_df["qqq_daily_return"]).sort_values()
        corr_result = pd.DataFrame({
            "지표":         [COLUMN_LABELS[c] for c in corr_series.index],
            "상관계수 (r)": corr_series.values.round(4),
            "해석":         [
                "강한 음의 상관 📉" if r < -0.5 else
                "중간 음의 상관 🔽" if r < -0.3 else
                "강한 양의 상관 📈" if r > 0.5 else
                "중간 양의 상관 🔼" if r > 0.3 else
                "약한 상관 ➡️"
                for r in corr_series.values
            ]
        })

        def color_corr(val):
            if isinstance(val, float):
                if val > 0.3:
                    return f"color: {'#28a745' if val > 0.5 else '#5cb85c'}; font-weight: bold"
                elif val < -0.3:
                    return f"color: {'#dc3545' if val < -0.5 else '#e57373'}; font-weight: bold"
            return ""

        styled = corr_result.style.applymap(color_corr, subset=["상관계수 (r)"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.caption(f"분석 기간: {len(corr_df)}일 | 데이터 기준: QQQ 당일 수익률과의 피어슨 상관계수")

    # ── 원본 데이터 테이블 ──────────────────────────
    st.markdown("---")
    with st.expander("🗃️ 원본 데이터 보기 / CSV 다운로드"):
        display_df = filtered.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.drop(columns=["collected_at_utc"], errors="ignore")
        display_df = display_df.rename(columns=COLUMN_LABELS)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_bytes = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️ CSV 다운로드",
            data=csv_bytes,
            file_name=f"market_indicators_{start}_{end}.csv",
            mime="text/csv",
        )
