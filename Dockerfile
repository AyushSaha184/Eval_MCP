FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.MD alembic.ini ./
COPY prompts ./prompts
COPY scripts ./scripts
COPY src ./src
COPY server.py ./

RUN pip install --upgrade pip \
    && pip install .

CMD ["eval-mcp", "api"]
