
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import text

from .config import PAIRS, all_tickers
from .db import engine

log = logging.getLogger(__name__)

# Тикеры FX-пар: для них на дневных данных yfinance бывает разрыв
# close(t) → open(t+1) из-за «странных» границ суток на круглосуточном рынке.
# Сшиваем close с open следующего дня, чтобы свечной график был визуально
# непрерывным и без ложных гэпов. Контекстные тикеры (индексы/сырьё/ETF)
# имеют реальные разрывы и должны оставаться как есть.
FX_TICKERS: set[str] = set(PAIRS.values())


def _normalize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index().rename(
        columns={"Date": "ts", "Open": "open", "High": "high", "Low": "low", "Close": "close"}
    )
    keep = ["ts", "open", "high", "low", "close"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["ticker"] = ticker
    df["ts"] = pd.to_datetime(df["ts"]).dt.date
    df["close"] = df["open"].shift(-1)
    for c in ("open", "high", "low", "close"):
        df.loc[df[c] < 0, c] = np.nan
    df["close"] = df["close"].clip(lower=df["low"], upper=df["high"])
    df = df.dropna(subset=["close"])
    return df


def _fetch_one(ticker: str, start: str) -> pd.DataFrame:
    try:
        raw = yf.download(
            ticker, start=start, interval="1d", progress=False, auto_adjust=False, threads=False
        )
    except Exception as exc:
        log.warning("yfinance failed for %s: %s", ticker, exc)
        return pd.DataFrame()
    return _normalize(raw, ticker)


def _upsert(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    rows = df[["ts", "ticker", "open", "high", "low", "close"]].to_dict("records")
    sql = text(
        """
        INSERT INTO prices (ts, ticker, open, high, low, close)
        VALUES (:ts, :ticker, :open, :high, :low, :close)
        ON CONFLICT (ts, ticker) DO UPDATE SET
            open = EXCLUDED.open, high = EXCLUDED.high,
            low = EXCLUDED.low, close = EXCLUDED.close
        """
    )
    with engine().begin() as conn:
        conn.execute(sql, rows)
    return len(rows)


def _log_run(job: str, status: str, rows: int, message: str = "", started: datetime | None = None) -> None:
    sql = text(
        "INSERT INTO etl_log (job, started_at, finished_at, status, rows, message) "
        "VALUES (:job, :s, :f, :st, :r, :m)"
    )
    now = datetime.now(timezone.utc)
    with engine().begin() as conn:
        conn.execute(sql, {"job": job, "s": started or now, "f": now,
                           "st": status, "r": rows, "m": message[:500]})


def run_load(start: str | None = None) -> int:
    """Download every tracked ticker and upsert into Postgres. Returns rows written."""
    started = datetime.now(timezone.utc)
    start = start or os.environ.get("DATA_START_DATE", "2010-01-01")
    total = 0
    failures: list[str] = []
    for t in all_tickers():
        df = _fetch_one(t, start)
        if df.empty:
            failures.append(t)
            continue
        # drop the last (potentially incomplete) row
        df = df.iloc[:-1] if len(df) > 1 else df
        total += _upsert(df)
    msg = "ok" if not failures else f"missing: {','.join(failures)}"
    _log_run("loader", "success", total, msg, started)
    log.info("loader done rows=%d %s", total, msg)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_load()
