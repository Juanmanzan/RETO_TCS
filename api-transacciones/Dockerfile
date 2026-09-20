FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["/bin/sh","-c","rm -rf \"${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus-multiproc}\" && mkdir -p \"${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus-multiproc}\" && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log"]
