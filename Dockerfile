FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY server/ server/
COPY client.py .
COPY __init__.py .
COPY openenv.yaml .

RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir fastmcp fastapi uvicorn pydantic numpy requests

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
