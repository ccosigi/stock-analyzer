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

    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="⬇️ CSV 다운로드",
        data=csv_bytes,
        file_name="market_indicators.csv",
        mime="text/csv",
    )

    # ── 정규화 차트 ─────────────────────────────────
    st.markdown("---")
    st.subheader("📊 지표 추이 비교 (정규화)")

    available = {k: v for k, v in CHART_COLS.items() if k in df.columns}
    chart_data = df.set_index("date")[list(available.keys())].rename(columns=available)

    # Min-Max 정규화 (0~1)
    chart_normalized = (chart_data - chart_data.min()) / (chart_data.max() - chart_data.min())

    st.line_chart(chart_normalized)
    st.caption("모든 지표를 0~1로 정규화하여 변화 추이를 비교합니다.")
