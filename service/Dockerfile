FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY vendor/sqlite-dissect ./vendor/sqlite-dissect
COPY src ./src
COPY service ./service

RUN uv sync --no-dev

EXPOSE 8090

CMD ["uv", "run", "uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8090"]
