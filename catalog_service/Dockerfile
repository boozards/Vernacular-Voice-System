FROM python:3.12-slim as builder

WORKDIR /app
COPY catalog_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
RUN useradd -m voicekart && chown -R voicekart:voicekart /app

COPY --from=builder /install /usr/local
COPY shared /app/shared
COPY catalog_service /app/catalog_service

ENV PYTHONPATH=/app
USER voicekart

EXPOSE 8005

CMD ["uvicorn", "catalog_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
