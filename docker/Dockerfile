FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    procps \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

CMD ["bash"]
