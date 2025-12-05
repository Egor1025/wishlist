ARG PYTHON_BASE=python:3.11.14-slim-bookworm@sha256:50068b28f3105e4a3116e091993304eccb38895d676c8dae174c5b01a4d30dfb

FROM ${PYTHON_BASE} AS build
WORKDIR /api
COPY pyproject.toml .
COPY app ./app
COPY tests ./tests
RUN pip install --no-cache-dir .[dev]
RUN python -m build --wheel
RUN mkdir -p ./db
RUN pytest -q


FROM ${PYTHON_BASE}
WORKDIR /api
RUN useradd -m appuser

COPY --from=build /api/dist /dist
COPY --from=build /api/app ./app

RUN mkdir -p /api/db && chown appuser:appuser /api/db
RUN pip install --no-cache-dir /dist/*.whl

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6000"]
