
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text

from shared.config import PAIRS, PAIR_CONTEXT
from shared.db import engine

app = FastAPI(title="FX Volatility API", version="1.0")


@app.get("/health")
def health():
    try:
        with engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(503, f"db unavailable: {exc}")


@app.get("/pairs")
def list_pairs():
    return [{"pair": p, "ticker": t, "context": PAIR_CONTEXT[p]} for p, t in PAIRS.items()]


@app.get("/history/{pair:path}")
def history(pair: str, start: Optional[date] = None, end: Optional[date] = None):
    if pair not in PAIRS:
        raise HTTPException(404, "unknown pair")
    sql = "SELECT ts, open, high, low, close FROM prices WHERE ticker = :t"
    params = {"t": PAIRS[pair]}
    if start:
        sql += " AND ts >= :s"
        params["s"] = start
    if end:
        sql += " AND ts <= :e"
        params["e"] = end
    sql += " ORDER BY ts"
    with engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict("records")


@app.get("/context/{pair:path}")
def context(pair: str, start: Optional[date] = None, end: Optional[date] = None):
    if pair not in PAIRS:
        raise HTTPException(404, "unknown pair")
    tickers = PAIR_CONTEXT[pair]
    sql = "SELECT ts, ticker, close FROM prices WHERE ticker = ANY(:tt)"
    params: dict = {"tt": tickers}
    if start:
        sql += " AND ts >= :s"
        params["s"] = start
    if end:
        sql += " AND ts <= :e"
        params["e"] = end
    sql += " ORDER BY ticker, ts"
    with engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.to_dict("records")


@app.get("/predictions/{pair:path}")
def predictions(pair: str,
                start: Optional[date] = None,
                end: Optional[date] = None,
                limit: int = Query(2000, ge=1, le=20000)):
    if pair not in PAIRS:
        raise HTTPException(404, "unknown pair")
    sql = ("SELECT ts, realized_vol, predicted_vol, vol_index, predicted_index "
           "FROM predictions WHERE pair = :p")
    params: dict = {"p": pair}
    if start:
        sql += " AND ts >= :s"; params["s"] = start
    if end:
        sql += " AND ts <= :e"; params["e"] = end
    sql += " ORDER BY ts DESC LIMIT :lim"
    params["lim"] = limit
    with engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
    return df.sort_values("ts").to_dict("records")


@app.get("/latest/{pair:path}")
def latest(pair: str):
    """Compact summary card for the dashboard: last close, change, current
    realized vol, model's next-day forecast, both as 1..100 indices."""
    if pair not in PAIRS:
        raise HTTPException(404, "unknown pair")
    with engine().connect() as conn:
        price_rows = conn.execute(
            text("SELECT ts, close FROM prices WHERE ticker = :t ORDER BY ts DESC LIMIT 2"),
            {"t": PAIRS[pair]},
        ).all()
        pred_row = conn.execute(
            text("SELECT ts, realized_vol, predicted_vol, vol_index, predicted_index "
                 "FROM predictions WHERE pair = :p ORDER BY ts DESC LIMIT 1"),
            {"p": pair},
        ).one_or_none()
    if not price_rows:
        raise HTTPException(404, "no price data")
    last_close = float(price_rows[0][1])
    prev_close = float(price_rows[1][1]) if len(price_rows) == 2 else last_close
    change_pct = (last_close / prev_close - 1) * 100 if prev_close else 0.0
    return {
        "pair": pair,
        "last_ts": price_rows[0][0].isoformat(),
        "last_close": last_close,
        "change_pct": change_pct,
        "realized_vol": float(pred_row[1]) if pred_row else None,
        "predicted_vol": float(pred_row[2]) if pred_row else None,
        "vol_index": float(pred_row[3]) if pred_row and pred_row[3] is not None else None,
        "predicted_index": float(pred_row[4]) if pred_row and pred_row[4] is not None else None,
    }


@app.get("/etl/stats")
def etl_stats(days: int = Query(30, ge=1, le=365)):
    sql = text(
        "SELECT job, status, COUNT(*) AS n, MAX(finished_at) AS last_run "
        "FROM etl_log WHERE started_at >= NOW() - (:d || ' days')::interval "
        "GROUP BY job, status ORDER BY job, status"
    )
    with engine().connect() as conn:
        rows = conn.execute(sql, {"d": days}).mappings().all()
    return [dict(r) for r in rows]
