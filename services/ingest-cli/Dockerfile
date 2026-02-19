FROM python:3.14-slim

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false \
  && poetry install --no-root --only main

COPY src /app/src

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "src.main"]
