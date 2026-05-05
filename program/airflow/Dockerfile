FROM apache/airflow:2.10.2-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Устанавливаем зависимости shared/ под constraints Airflow,
# чтобы не сломать pin SQLAlchemy 1.4.x и других core-библиотек.
COPY airflow/requirements.txt /tmp/airflow-extra-requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.2/constraints-3.11.txt" \
    -r /tmp/airflow-extra-requirements.txt
