FROM python:3.9-slim

LABEL authors="nikolai"

WORKDIR /cash_registers

COPY . /cash_registers

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*
CMD ["python", "Work_tasks.py"]

EXPOSE 8002
