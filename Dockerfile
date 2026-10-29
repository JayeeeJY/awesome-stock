# Experimental image for Linux, Windows and macOS. The ledger uses the Python
# standard library only. The browser UI is the committed frontend/owner-ui/dist.
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Awesome Stock" \
      org.opencontainers.image.description="Local AI investing journal. Not a stock picker." \
      org.opencontainers.image.source="https://github.com/JayeeeJY/awesome-stock" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY start_owner.py /app/start_owner.py
COPY backend /app/backend
COPY frontend /app/frontend
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod 755 /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data \
    && chmod 700 /data \
    && python3 -c "import pathlib; assert pathlib.Path('/app/frontend/owner-ui/dist/index.html').is_file()"

VOLUME /data
EXPOSE 4322

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4322/api/v1/health', timeout=2).read()"

ENTRYPOINT ["docker-entrypoint.sh"]
