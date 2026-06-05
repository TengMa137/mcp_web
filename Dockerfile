FROM python:3.11-slim

# Install system dependencies for Crawl4AI
RUN apt-get update && apt-get install -y \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN mkdir -p /ms-playwright \
    && playwright install chromium

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/home/app

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /home/app/.cache /tmp \
    && chown -R app:app /app /home/app /ms-playwright

USER app

# Default: run server
CMD ["python", "server.py"]
