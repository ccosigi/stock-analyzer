import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

def normalize(col):
    col_range = col.max() - col.min()
    return (col - col.min()) / col_range * 100 if col_range != 0 else col * 0 + 50

def history_tab():
    st.markdown('<div class="sub-header">📈 일별 시장 지표 히스토리</div>', unsafe_allow_html=True)

    df = load_history()

    if df is None or df.empty:
        st.warning("아직 수집된 데이터가 없습니다.")
        return

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

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for key in selected:
        label = available[key]
        is_qqq = key == "qqq_price"
        raw = df[key]
        y = raw if is_qqq else normalize(raw)

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=y,
                name=label,
                mode="lines+markers",
                line=dict(color=COLORS[key], width=2),
                customdata=raw,
                hovertemplate=(
                    f"{label}: $%{{customdata:.2f}}<extra></extra>"
                    if is_qqq else
                    f"{label}: %{{customdata:.2f}} (정규화: %{{y:.1f}})<extra></extra>"
                ),
            ),
            secondary_y=is_qqq,
        )

    fig.update_layout(
        yaxis=dict(
            title="정규화 (0~100)",
            range=[0, 100],
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis2=dict(
            title="나스닥 QQQ ($)",
            showgrid=False,
            color=COLORS["qqq_price"],
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
    st.caption("왼쪽: VIX · FGI · RSI 정규화 (0~100) | 오른쪽: 나스닥 QQQ 실제 가격 | hover시 실제값 표시")

    st.markdown("---")
    with st.expander("🗃️ 상세 데이터 보기"):
        display_df = df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.drop(columns=["collected_at_utc"], errors="ignore")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
