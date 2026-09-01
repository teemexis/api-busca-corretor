FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    DISPLAY=:99 \
    DOCKER=true \
    PLAYWRIGHT_HEADLESS=false \
    SCRAPER_MAX_ATTEMPTS=3

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts/start.sh ./scripts/start.sh
RUN chmod +x ./scripts/start.sh

EXPOSE 8000

CMD ["bash", "scripts/start.sh"]
