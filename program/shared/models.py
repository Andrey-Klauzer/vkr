"""Volatility models from the research notebook.

GJR-GARCH(1,1) skewed-t with online Ridge calibration on HAR features.

The 1..100 volatility index is an expanding min-max scaling of realized_vol;
the first WARMUP_BURN points are nulled because expanding stats are unstable.

`run_predict()` is incremental: it reuses already-stored predicted_vol values
for dates already in the `predictions` table and only refits GARCH for new
days. Realized-vol and the expanding index are always recomputed from the
full price history because they are cheap.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from arch import arch_model
from sklearn.linear_model import Ridge
from sqlalchemy import text

from .config import PAIRS
from .db import engine

log = logging.getLogger(__name__)

WINDOW = 252           # GARCH rolling fit window
CALIB_WINDOW = 500     # Ridge online window
WARMUP_BURN = 100      # initial expanding-window predictions to discard for the index
RECOMPUTE_TAIL = 5     # refresh forecasts for the last N stored dates


def _load_pair_close(pair: str) -> pd.DataFrame:
    ticker = PAIRS[pair]
    sql = text("SELECT ts, close FROM prices WHERE ticker = :t ORDER BY ts")
    with engine().connect() as conn:
        df = pd.read_sql(sql, conn, params={"t": ticker})
    df["ts"] = pd.to_datetime(df["ts"])
    return df.set_index("ts")


def _load_existing_predicted(pair: str) -> dict:
    sql = text("SELECT ts, predicted_vol FROM predictions WHERE pair = :p")
    with engine().connect() as conn:
        rows = conn.execute(sql, {"p": pair}).all()
    return {pd.Timestamp(r[0]): float(r[1]) for r in rows if r[1] is not None}


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["close"] = out["close"].astype(float)
    out["returns"] = np.log(out["close"] / out["close"].shift(1))
    out["realized_vol"] = out["returns"].rolling(20).std()
    out["rv_lag1"] = out["realized_vol"].shift(1)
    out["rv_lag5"] = out["realized_vol"].shift(5)
    out["rv_lag21"] = out["realized_vol"].shift(21)
    return out.dropna()


def _fit_one_step(returns_window: pd.Series) -> float:
    try:
        m = arch_model(returns_window, vol="GARCH", p=1, o=1, q=1, dist="skewt", rescale=False)
        res = m.fit(disp="off", show_warning=False)
        var_fc = float(res.forecast(horizon=1, reindex=False).variance.values[-1].mean())
    except Exception:
        var_fc = float(returns_window.ewm(alpha=0.06, adjust=False).var().iloc[-1])
    return np.sqrt(var_fc) / 100.0


def _predict_pair(pair: str) -> pd.DataFrame:
    raw = _load_pair_close(pair)
    if len(raw) < WINDOW + 30:
        return pd.DataFrame()
    df = _prepare(raw)
    if len(df) <= WINDOW:
        return pd.DataFrame()

    returns_pct = df["returns"] * 100
    cached = _load_existing_predicted(pair)
    last_cached_ts = max(cached) if cached else None

    garch_hist: list[float] = []
    rv_l1, rv_l5, rv_l21, rv_actual = [], [], [], []
    out_rows = []

    for i in range(WINDOW, len(df)):
        ts = df.index[i]
        f1, f5, f21 = df["rv_lag1"].iat[i], df["rv_lag5"].iat[i], df["rv_lag21"].iat[i]

        # Decide whether we need to actually refit GARCH for this point.
        is_recent = (last_cached_ts is None) or (ts > last_cached_ts - pd.Timedelta(days=RECOMPUTE_TAIL))
        cached_pred = cached.get(ts)

        if cached_pred is not None and not is_recent:
            calibrated = cached_pred
            # We don't have garch_raw on disk, approximate buffer with the calibrated value.
            garch_hist.append(cached_pred)
        else:
            garch_today = _fit_one_step(returns_pct.iloc[i - WINDOW:i])
            if len(garch_hist) >= 30:
                X = np.column_stack([garch_hist, rv_l1, rv_l5, rv_l21])
                y = np.array(rv_actual)
                n = min(CALIB_WINDOW, len(y))
                ridge = Ridge(alpha=1e-4).fit(X[-n:], y[-n:])
                calibrated = float(ridge.predict([[garch_today, f1, f5, f21]])[0])
            else:
                calibrated = garch_today
            garch_hist.append(garch_today)

        rv_l1.append(f1); rv_l5.append(f5); rv_l21.append(f21)
        rv_actual.append(float(df["realized_vol"].iat[i]))

        out_rows.append({
            "ts": ts.date(),
            "pair": pair,
            "realized_vol": float(df["realized_vol"].iat[i]),
            "predicted_vol": max(0.0, calibrated),
        })

    out = pd.DataFrame(out_rows)
    if out.empty:
        return out

    # Winsorized expanding 1..100 index. Plain expanding min/max gets dominated
    # by one-off spikes (e.g. RUB-2022) and squashes everything else to ~0;
    # 1st/99th percentiles keep the scale interpretable.
    rv_series = out["realized_vol"]
    rv_low = rv_series.expanding().quantile(0.01)
    rv_high = rv_series.expanding().quantile(0.99)
    span = (rv_high - rv_low).replace(0, np.nan)
    out["vol_index"] = (1 + 99 * (rv_series - rv_low) / span).clip(1, 100)
    out["predicted_index"] = (1 + 99 * (out["predicted_vol"] - rv_low) / span).clip(1, 100)
    if len(out) > WARMUP_BURN:
        out.loc[: WARMUP_BURN - 1, ["vol_index", "predicted_index"]] = np.nan

    return out


def _upsert_predictions(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    sql = text(
        """
        INSERT INTO predictions (ts, pair, realized_vol, predicted_vol, vol_index, predicted_index)
        VALUES (:ts, :pair, :realized_vol, :predicted_vol, :vol_index, :predicted_index)
        ON CONFLICT (ts, pair) DO UPDATE SET
            realized_vol    = EXCLUDED.realized_vol,
            predicted_vol   = EXCLUDED.predicted_vol,
            vol_index       = EXCLUDED.vol_index,
            predicted_index = EXCLUDED.predicted_index
        """
    )
    rows = df.where(pd.notna(df), None).to_dict("records")
    with engine().begin() as conn:
        conn.execute(sql, rows)
    return len(rows)


def _log_run(status: str, rows: int, message: str, started: datetime) -> None:
    with engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO etl_log (job, started_at, finished_at, status, rows, message) "
                "VALUES ('predictor', :s, :f, :st, :r, :m)"
            ),
            {"s": started, "f": datetime.now(timezone.utc),
             "st": status, "r": rows, "m": message[:500]},
        )


def run_predict() -> int:
    started = datetime.now(timezone.utc)
    total = 0
    errors: list[str] = []
    for pair in PAIRS:
        try:
            df = _predict_pair(pair)
            total += _upsert_predictions(df)
            log.info("predicted %s rows=%d", pair, len(df))
        except Exception as exc:
            errors.append(f"{pair}:{exc}")
            log.exception("predict failed for %s", pair)
    msg = "ok" if not errors else " | ".join(errors)
    _log_run("success" if not errors else "partial", total, msg, started)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_predict()
