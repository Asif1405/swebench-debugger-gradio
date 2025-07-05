FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y \
      git curl gnupg lsb-release ca-certificates \
      && curl -fsSL https://download.docker.com/linux/debian/gpg \
         | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
      && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
         https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
         | tee /etc/apt/sources.list.d/docker.list > /dev/null \
      && apt-get update && apt-get install -y docker-ce-cli \
      && apt-get install -y su-exec \
      && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /usr/local/bin/entrypoint.sh

USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/ || exit 1

RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["python", "app.py"]
