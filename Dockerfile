# BUILD STAGE
# UPDATED: Changed from 3.10 to 3.11 to support numpy>=2.3.0
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libgtk-3-0 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
# BUILD STAGE
# UPDATED: Changed from 3.10 to 3.11 to support numpy>=2.3.0
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libgtk-3-0 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

# RUNTIME STAGE
# UPDATED: Changed from 3.10 to 3.11
FROM python:3.11-slim
WORKDIR /app

# CRITICAL UPDATE: Changed path from /python3.10/ to /python3.11/
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /app /app

# install playwright browsers
RUN python -m playwright install chromium
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--log-level", "info"]