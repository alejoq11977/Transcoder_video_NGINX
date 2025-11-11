FROM python:3.9-slim

RUN apt-get update && apt-get install -y iputils-ping

WORKDIR /app

COPY api_server/requirements.txt /app/requirements.txt
COPY proto /app/proto

RUN pip install --no-cache-dir -r requirements.txt

COPY api_server/ /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
