FROM python:3.11.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 10001 app \
 && adduser --system --uid 10001 --ingroup app --home /nonexistent --shell /usr/sbin/nologin app

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN pip install -U pip \
 && pip install .

RUN mkdir -p /app/db \
 && chown -R app:app /app

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]