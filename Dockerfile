FROM python:3.12-slim

LABEL org.opencontainers.image.title="Folder Galaxy" \
      org.opencontainers.image.description="A live 3D constellation of your folders and files" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY server.py .
COPY static ./static

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765

EXPOSE 8765
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=4)"

ENTRYPOINT ["python", "server.py"]
