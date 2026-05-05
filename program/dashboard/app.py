
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

from shared.config import PAIRS, PAIR_CONTEXT
from shared.db import engine

BLUE = "#1f4e79"
LIGHT_BLUE = "#5a8fbf"
GREEN = "#2e8b57"
RED = "#c0504d"
GREY = "#7a8a99"

RUS_MONTHS = {1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
              7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"}
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

st.set_page_config(
    page_title="Мониторинг волатильности FX",
    layout="wide",
    page_icon="💱",
)

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .stMetric label { color: #1f4e79 !important; font-weight: 600; }
        .stMetric { background: #EBF2FA; border-radius: 8px; padding: 8px 12px; }
        h1, h2, h3 { color: #1f4e79; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_prices(ticker: str, start: date, end: date) -> pd.DataFrame:
    sql = text(
        "SELECT ts, open, high, low, close FROM prices "
        "WHERE ticker = :t AND ts BETWEEN :s AND :e ORDER BY ts"
    )
    with engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"t": ticker, "s": start, "e": end})
    df["ts"] = pd.to_datetime(df["ts"])
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_predictions(pair: str, start: date, end: date) -> pd.DataFrame:
    sql = text(
        "SELECT ts, realized_vol, predicted_vol, vol_index, predicted_index "
        "FROM predictions WHERE pair = :p AND ts BETWEEN :s AND :e ORDER BY ts"
    )
    with engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"p": pair, "s": start, "e": end})
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def russian_dates(ts: pd.Series) -> list[str]:
    """For hover tooltips: 'пт, 01 мая 2026'."""
    out = []
    for t in ts:
        out.append(f"{WEEKDAYS[t.weekday()]}, {t.day:02d} {RUS_MONTHS[t.month]} {t.year}")
    return out


def russian_axis(ts: pd.Series) -> tuple[list, list]:
    """Build monthly tickvals/ticktext in Russian, thinning when needed."""
    if len(ts) == 0:
        return [], []
    months = pd.date_range(ts.min().normalize().replace(day=1),
                           ts.max(), freq="MS")
    if len(months) > 18:
        step = max(1, len(months) // 9)
        months = months[::step]
    text = [f"{RUS_MONTHS[m.month]} {m.year % 100:02d}" for m in months]
    return list(months), text


st.title("💱  Мониторинг волатильности FX (валютного рынка)")

with st.sidebar:
    st.header("Настройки")
    pair = st.selectbox("Валютная пара", list(PAIRS), index=0)
    period_label = st.radio(
        "Период",
        ["1 месяц", "3 месяца", "6 месяцев", "1 год", "3 года"],
        index=3,
    )
    period_days = {"1 месяц": 30, "3 месяца": 90, "6 месяцев": 180,
                   "1 год": 365, "3 года": 365 * 3}[period_label]

end = date.today()
start = end - timedelta(days=period_days)

prices = load_prices(PAIRS[pair], start, end)
preds = load_predictions(pair, start, end)

if prices.empty:
    st.warning(
        "Данных пока нет. Запустите DAG `fx_pipeline` в Airflow "
        "(http://localhost:8080) и обновите страницу через несколько минут."
    )
    st.stop()


# ----- KPI row ------------------------------------------------------------- #
last_close = float(prices["close"].iloc[-1])
prev_close = float(prices["close"].iloc[-2]) if len(prices) > 1 else last_close
change_pct = (last_close / prev_close - 1) * 100

idx_now_raw = preds["vol_index"].dropna().iloc[-1] if not preds["vol_index"].dropna().empty else None
idx_next_raw = preds["predicted_index"].dropna().iloc[-1] if not preds["predicted_index"].dropna().empty else None
idx_now = round(idx_now_raw) if idx_now_raw is not None else None
idx_next = round(idx_next_raw) if idx_next_raw is not None else None
delta_idx = (idx_next - idx_now) if (idx_now is not None and idx_next is not None) else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Последняя цена", f"{last_close:.5f}", f"{change_pct:+.2f}%")
c2.metric("Реализ. волатильность (20д)",
          f"{preds['realized_vol'].iloc[-1] * 100:.2f}%" if not preds.empty else "—")
c3.metric("Индекс волатильности (1–100)",
          f"{idx_now}" if idx_now is not None else "—")
c4.metric("Прогноз на завтра (1–100)",
          f"{idx_next}" if idx_next is not None else "—",
          (f"{delta_idx:+d}" if delta_idx not in (None, 0) else None))


def candlestick(df: pd.DataFrame, name: str, height: int = 380, compact: bool = False) -> go.Figure:
    tickvals, ticktext = russian_axis(df["ts"])
    rdates = russian_dates(df["ts"])
    # Candlestick traces don't support hovertemplate — assemble the tooltip
    # text ourselves and pass it via `text` with `hoverinfo='text'`.
    hover_text = [
        f"<b>{d}</b><br>Открытие: {o:.5f}<br>Максимум: {h:.5f}<br>"
        f"Минимум: {l:.5f}<br>Закрытие: {c:.5f}"
        for d, o, h, l, c in zip(
            rdates, df["open"], df["high"], df["low"], df["close"]
        )
    ]
    fig = go.Figure(go.Candlestick(
        x=df["ts"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing=dict(line=dict(color=GREEN, width=1), fillcolor=GREEN),
        decreasing=dict(line=dict(color=RED, width=1), fillcolor=RED),
        name=name,
        text=hover_text,
        hoverinfo="text",
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8 if not compact else 4),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(
            showgrid=True, gridcolor="#E5ECF4",
            tickvals=tickvals, ticktext=ticktext,
            rangeslider=dict(visible=False),
            title=None,
        ),
        yaxis=dict(showgrid=True, gridcolor="#E5ECF4", title=None),
        hovermode="x unified",
        showlegend=False,
    )
    return fig


st.subheader(f"Курс {pair}")
st.plotly_chart(candlestick(prices, pair, height=400), use_container_width=True)


g1, g2 = st.columns([1, 2])
with g1:
    if idx_now is not None:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=float(idx_now),
            number={"font": {"color": BLUE, "size": 48}},
            title={"text": "Индекс волатильности", "font": {"color": BLUE, "size": 16}},
            gauge={
                "axis": {"range": [1, 100], "tickcolor": GREY},
                "bar": {"color": BLUE},
                "steps": [
                    {"range": [1, 30], "color": "#D7E5F2"},
                    {"range": [30, 70], "color": "#9DBDDC"},
                    {"range": [70, 100], "color": "#C97A7A"},
                ],
            },
        ))
        gauge.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10),
                            paper_bgcolor="white")
        st.plotly_chart(gauge, use_container_width=True)

with g2:
    st.markdown("**Динамика индекса волатильности**")
    if not preds.empty:
        tickvals, ticktext = russian_axis(preds["ts"])
        hover = russian_dates(preds["ts"])
        fig_idx = go.Figure()
        fig_idx.add_trace(go.Scatter(
            x=preds["ts"], y=preds["vol_index"], mode="lines",
            name="Реализованный", line=dict(color=BLUE, width=2),
            customdata=hover,
            hovertemplate="<b>%{customdata}</b><br>Реализованный: %{y:.0f}<extra></extra>",
        ))
        fig_idx.add_trace(go.Scatter(
            x=preds["ts"], y=preds["predicted_index"], mode="lines",
            name="Прогноз", line=dict(color=LIGHT_BLUE, width=1.6, dash="dash"),
            customdata=hover,
            hovertemplate="<b>%{customdata}</b><br>Прогноз: %{y:.0f}<extra></extra>",
        ))
        fig_idx.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#E5ECF4"),
            xaxis=dict(showgrid=True, gridcolor="#E5ECF4",
                       tickvals=tickvals, ticktext=ticktext),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
            hovermode="x unified",
        )
        st.plotly_chart(fig_idx, use_container_width=True)


st.subheader("Драйверы волатильности")
ctx_tickers = PAIR_CONTEXT[pair]
cols = st.columns(len(ctx_tickers))
for col, ticker in zip(cols, ctx_tickers):
    df_c = load_prices(ticker, start, end)
    with col:
        if df_c.empty:
            st.info(f"{ticker}: нет данных")
            continue
        last = float(df_c["close"].iloc[-1])
        prev = float(df_c["close"].iloc[-2]) if len(df_c) > 1 else last
        chg = (last / prev - 1) * 100
        st.metric(label=ticker, value=f"{last:.4g}", delta=f"{chg:+.2f}%")
        st.plotly_chart(candlestick(df_c, ticker, height=220, compact=True),
                        use_container_width=True)

st.caption(
    f"Источник данных: Yahoo Finance · обновляется ежедневно через Airflow · "
    f"API: {os.environ.get('API_PUBLIC_URL', 'http://localhost:8000')}"
)
