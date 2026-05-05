
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from shared.loader import run_load
from shared.models import run_predict


default_args = {
    "owner": "fx",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}

with DAG(
    dag_id="fx_pipeline",
    description="Load FX prices from Yahoo Finance and refresh volatility predictions.",
    start_date=datetime(2024, 1, 1),
    schedule="0 22 * * *",     # 22:00 UTC daily, after US close
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["fx", "volatility"],
) as dag:

    load = PythonOperator(task_id="load_prices", python_callable=run_load)
    predict = PythonOperator(task_id="predict_volatility", python_callable=run_predict)

    load >> predict
