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

RIGHT_AXIS = {"qqq_price"}

COLORS = {
    "vix":       "#e74c3c",
    "fgi":       "#f39c12",
    "spy_rsi":   "#3498db",
    "qqq_price": "#2ecc71",
}

# 지표별 y축 고정 범위
Y_RANGE = {
    "vix":       [0, 80],
    "fgi":       [0, 100],
    "spy_rsi":   [0, 100],
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

    # 지표 선택 (차트 위)
    selected = st.multiselect(
        "표시할 지표 선택",
        options=list(available.keys()),
        default=list(available.keys()),
        format_func=lambda x: available[x],
    )

    if not selected:
        st.info("지표를 하나 이상 선택하세요.")
        return

    # 왼쪽 y축 범위: 선택된 지표 중 고정범위 있는 것 기준
    left_selected = [k for k in selected if k not in RIGHT_AXIS]
    left_min = 0
    left_max = max([Y_RANGE[k][1] for k in left_selected if k in Y_RANGE], default=100)

    # 오른쪽 y축 범위: 나스닥 실제 데이터 기준 + 여백
    qqq_data = df["qqq_price"] if "qqq_price" in df.columns else None
    if qqq_data is not None:
        qqq_min = qqq_data.min() * 0.98
        qqq_max = qqq_data.max() * 1.02
    else:
        qqq_min, qqq_max = 0, 1

    fig = go.Figure()

    for key in selected:
        label = available[key]
        is_right = key in RIGHT_AXIS
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df[key],
            name=label,
            yaxis="y2" if is_right else "y1",
            line=dict(color=COLORS.get(key), width=2),
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
        ))

    fig.update_layout(
        yaxis=dict(
            title="지표 값",
            side="left",
            range=[left_min, left_max],
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis2=dict(
            title="나스닥 (QQQ)",
            side="right",
            overlaying="y",
            range=[qqq_min, qqq_max],
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=40, b=0),
        height=450,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("나스닥(QQQ)은 오른쪽 y축 기준 | VIX: 0~80 | FGI·RSI: 0~100")
