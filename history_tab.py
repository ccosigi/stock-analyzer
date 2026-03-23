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

def zscore_to_100(col):
    z = (col - col.mean()) / col.std()
    return ((z + 3) / 6 * 100).clip(0, 100)

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

    left_vals = []
    right_vals = []

    for key in selected:
        label = available[key]
        is_qqq = key == "qqq_price"
        raw = df[key].dropna()

        if is_qqq:
            y = df[key]
            right_vals.extend(raw.tolist())
        elif key == "vix":
            y = zscore_to_100(df[key])
            left_vals.extend(y.dropna().tolist())
        else:
            y = df[key]
            left_vals.extend(raw.tolist())

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=y,
                name=label,
                mode="lines+markers",
                line=dict(color=COLORS[key], width=2),
                customdata=df[key],
                hovertemplate=(
                    f"{label}: $%{{customdata:.2f}}<extra></extra>"
                    if is_qqq else
                    f"{label}: %{{customdata:.2f}}<extra></extra>"
                ),
            ),
            secondary_y=is_qqq,
        )

    # 선택된 지표 기준 오토스케일
    left_min = max(0, min(left_vals) * 0.95) if left_vals else 0
    left_max = min(100, max(left_vals) * 1.05) if left_vals else 100
    right_min = min(right_vals) * 0.98 if right_vals else None
    right_max = max(right_vals) * 1.02 if right_vals else None

    fig.update_layout(
        yaxis=dict(
            title="지표 값",
            range=[left_min, left_max],
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            tickformat="%Y-%m-%d",
            hoverformat="%Y-%m-%d"
        ),
        yaxis2=dict(
            title="나스닥 QQQ ($)",
            range=[right_min, right_max],
            showgrid=False,
            color=COLORS["qqq_price"],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=0, r=0, t=40, b=0),
        height=450,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)", hoverformat="%Y-%m-%d",
    ),

    st.plotly_chart(fig, use_container_width=True)
    st.caption("VIX: Z-스코어→0~100 변환 · FGI · RSI 실제값 | 오른쪽: 나스닥 QQQ 실제 가격")

    st.markdown("---")
    with st.expander("🗃️ 상세 데이터 보기"):
        display_df = df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.drop(columns=["collected_at_utc"], errors="ignore")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
