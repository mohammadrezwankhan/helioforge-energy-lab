FROM node:22-bookworm-slim AS web
WORKDIR /repo
COPY apps/web/package*.json ./apps/web/
RUN cd apps/web && npm ci
COPY apps/web ./apps/web
COPY scripts/build-web.mjs ./scripts/build-web.mjs
RUN cd apps/web && npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HELIOFORGE_DB=/data/helioforge.sqlite3
WORKDIR /repo
COPY apps/api ./apps/api
RUN pip install --no-cache-dir ./apps/api \
    && useradd --uid 10001 --create-home helioforge \
    && mkdir -p /data && chown helioforge:helioforge /data
COPY --from=web /repo/apps/web/dist ./apps/web/dist
ENV PYTHONPATH=/repo/apps/api
USER helioforge
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "helioforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
