FROM python:3.12-slim

WORKDIR /code

# Playwright chromium needs these at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libx11-6 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir . && pip uninstall -y jobscrap-backend

RUN playwright install chromium

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY companies.yaml .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
