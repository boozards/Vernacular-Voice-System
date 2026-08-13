FROM python:3.12-slim as builder

WORKDIR /app
COPY gateway_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
RUN useradd -m voicekart && chown -R voicekart:voicekart /app

COPY --from=builder /install /usr/local
COPY shared /app/shared
COPY gateway_service /app/gateway_service

ENV PYTHONPATH=/app
USER voicekart

EXPOSE 8001

CMD ["uvicorn", "gateway_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
