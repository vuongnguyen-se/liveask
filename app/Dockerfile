# Small, non-root image for LiveAsk. The same image runs the API, `migrate` and `cleanup`.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY liveask ./liveask

RUN useradd --uid 10001 --no-create-home appuser
USER 10001

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

EXPOSE 8000
CMD ["uvicorn", "liveask.main:app", "--host", "0.0.0.0", "--port", "8000"]
