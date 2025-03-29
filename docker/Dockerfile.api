FROM python:3.12-slim

ARG POETRY_VERSION=2.1.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    procps \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock /app/

RUN \
    pip install poetry==${POETRY_VERSION} && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

CMD ["bash"]
