FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg
WORKDIR /app

COPY worker_node/requirements.txt /app/requirements.txt
COPY proto /app/proto


RUN pip install --no-cache-dir -r requirements.txt

COPY worker_node/ /app

CMD ["python", "worker.py"]