FROM python:3.12-slim

WORKDIR /code

# pyproject alone is enough to resolve deps (builds an empty package, which
# we drop); keeps the dep layer cached across app code changes
COPY pyproject.toml .
RUN pip install --no-cache-dir . && pip uninstall -y jobscrap-backend

RUN playwright install --with-deps chromium

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY companies.yaml .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
