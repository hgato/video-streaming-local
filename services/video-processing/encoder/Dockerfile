FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false \
  && poetry install --no-root --only main

COPY src /app/src

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "src/main.py"]
