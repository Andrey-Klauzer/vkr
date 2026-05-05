CREATE TABLE IF NOT EXISTS prices (
    ts          DATE        NOT NULL,
    ticker      TEXT        NOT NULL,
    open        NUMERIC(20, 8),
    high        NUMERIC(20, 8),
    low         NUMERIC(20, 8),
    close       NUMERIC(20, 8),
    PRIMARY KEY (ts, ticker)
);
CREATE INDEX IF NOT EXISTS idx_prices_ticker_ts ON prices (ticker, ts);

CREATE TABLE IF NOT EXISTS predictions (
    ts                 DATE NOT NULL,
    pair               TEXT NOT NULL,
    realized_vol       DOUBLE PRECISION,
    predicted_vol      DOUBLE PRECISION,
    vol_index          DOUBLE PRECISION,
    predicted_index    DOUBLE PRECISION,
    PRIMARY KEY (ts, pair)
);

CREATE TABLE IF NOT EXISTS etl_log (
    id           SERIAL PRIMARY KEY,
    job          TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    status       TEXT NOT NULL,
    rows         INTEGER,
    message      TEXT
);
