FROM python:3.12-slim as builder

WORKDIR /app
COPY stt_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
# Install ffmpeg system library for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd -m voicekart && chown -R voicekart:voicekart /app

COPY --from=builder /install /usr/local
COPY shared /app/shared
COPY stt_service /app/stt_service

ENV PYTHONPATH=/app
USER voicekart

EXPOSE 8004

CMD ["uvicorn", "stt_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
