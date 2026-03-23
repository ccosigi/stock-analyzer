import streamlit as st
import pandas as pd
import plotly.graph_objects as go

HISTORY_CSV = "data/market_indicators.csv"

CHART_COLS = {
    "vix":       "VIX",
    "fgi":       "공포&탐욕 (FGI)",
    "spy_rsi":   "SPY RSI",
    "qqq_price": "나스닥 (QQQ)",
}

# 나스닥은 오른쪽 y축, 나머지는 왼쪽
RIGHT_AXIS = {"qqq_price"}

COLORS = {
    "vix":       "#e74c3c",
    "fgi":       "#f39c12",
    "spy_rsi":   "#3498db",
    "qqq_price": "#2ecc71",
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

    # 차트 먼저
    selected = st.session_state.get("selected_indicators", list(available.keys()))
    selected = [k for k in selected if k in available]
    if not selected:
        selected = list(available.keys())

    fig = go.Figure()

    for key in selected:
        label = available[key]
        yaxis = "y2" if key in RIGHT_AXIS else "y1"
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df[key],
            name=label,
            yaxis=yaxis,
            line=dict(color=COLORS.get(key), width=1.8),
        ))

    fig.update_layout(
        yaxis=dict(title="지표 값", side="left"),
        yaxis2=dict(title="나스닥 (QQQ)", side="right", overlaying="y"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=40, b=0),
        height=450,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("나스닥(QQQ)은 오른쪽 y축 기준입니다.")

    # 지표 선택은 차트 아래에
    selected_new = st.multiselect(
        "표시할 지표 선택",
        options=list(available.keys()),
        default=list(available.keys()),
        format_func=lambda x: available[x],
        key="selected_indicators",
    )
