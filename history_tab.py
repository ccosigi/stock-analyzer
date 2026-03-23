import streamlit as st
import pandas as pd

HISTORY_CSV = "data/market_indicators.csv"

CHART_COLS = {
    "vix":       "VIX",
    "fgi":       "공포&탐욕 (FGI)",
    "spy_rsi":   "SPY RSI",
    "qqq_price": "나스닥 (QQQ)",
}

@st.cache_data(ttl=3600)
def load_history():
    try:
        df = pd.read_csv(HISTORY_CSV, parse_dates=["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return None


def history_tab():
    st.markdown('<div class="sub-header">📈 일별 시장 지표 히스토리</div>', unsafe_allow_html=True)

    df = load_history()

    if df is None or df.empty:
        st.warning("아직 수집된 데이터가 없습니다.")
        return

    # ── 원본 데이터 테이블 ──────────────────────────
    st.subheader("🗃️ 원본 데이터")
    display_df = df.copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.drop(columns=["collected_at_utc"], errors="ignore")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── 차트 ────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 지표 추이 비교")

    available = {k: v for k, v in CHART_COLS.items() if k in df.columns}

    selected = st.multiselect(
        "표시할 지표 선택",
        options=list(available.keys()),
        default=list(available.keys()),
        format_func=lambda x: available[x],
    )

    if not selected:
        st.info("위에서 지표를 하나 이상 선택하세요.")
        return

    chart_data = df.set_index("date")[selected].rename(columns=available).copy()

    # 나스닥만 0~100으로 정규화
    qqq_label = "나스닥 (QQQ)"
    if qqq_label in chart_data.columns:
        col = chart_data[qqq_label]
        chart_data[qqq_label] = (col - col.min()) / (col.max() - col.min()) * 100

    st.line_chart(chart_data)
    st.caption("나스닥(QQQ)은 0~100으로 정규화하여 표시합니다.")
