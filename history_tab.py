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

def to_pct_change(col):
    """첫날 기준 변화율 (%)"""
    first = col.iloc[0]
    return (col - first) / first * 100 if first != 0 else col * 0

def history_tab():
    st.markdown('<div class="sub-header">📈 일별 시장 지표 히스토리</div>', unsafe_allow_html=True)

    df = load_history()

    if df is None or df.empty:
        st.warning("아직 수집된 데이터가 없습니다.")
        return

    # ── 차트 ────────────────────────────────────────
    st.subheader("📊 지표 추이 비교")

    available = {k: v for k, v in CHART_COLS.items() if k in df.columns}

    selected = st.multiselect(
        "표시할 지표 선택",
        options=list(available.keys()),
        default=list(available.keys()),
        format_func=lambda x: available[x],
    )

    if not selected:
        st.info("지표를 하나 이상 선택하세요.")
        return

    fig = go.Figure()

    for key in selected:
        label = available[key]
        raw = df[key]
        pct = to_pct_change(raw)

        if key == "qqq_price":
            hover = f"{label}: $%{{customdata:.2f}} (%{{y:+.2f}}%)<extra></extra>"
        else:
            hover = f"{label}: %{{customdata:.2f}} (%{{y:+.2f}}%)<extra></extra>"

        fig.add_trace(go.Scatter(
            x=df["date"],
            y=pct,
            name=label,
            mode="lines+markers",
            line=dict(color=COLORS[key], width=2),
            customdata=raw,
            hovertemplate=hover,
        ))

    # 기준선 0
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(128,128,128,0.4)", line_width=1)

    fig.update_layout(
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            title="첫날 대비 변화율 (%)",
            ticksuffix="%",
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
    st.caption("모든 지표 첫날 기준 변화율 | hover시 실제값 표시")

    # ── 원본 데이터 (숨김) ──────────────────────────
    st.markdown("---")
    with st.expander("🗃️ 상세 데이터 보기"):
        display_df = df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.drop(columns=["collected_at_utc"], errors="ignore")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

