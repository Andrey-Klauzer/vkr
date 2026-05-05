
import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@lru_cache(maxsize=1)
def engine() -> Engine:
    user = os.environ["POSTGRES_USER"]
    pw = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return create_engine(
        f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}",
        pool_pre_ping=True,
        future=True,
    )
