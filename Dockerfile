FROM python:3.11-slim

# Install system dependencies for Crawl4AI
RUN apt-get update && apt-get install -y \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN playwright install chromium || true

# Copy application code
COPY models.py .
COPY tools/ ./tools/
COPY server.py .
COPY client.py .

ENV PYTHONUNBUFFERED=1

# Default: run server
CMD ["python", "server.py"]
