FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
COPY matter_hub ./matter_hub
RUN uv pip install --system -e .
EXPOSE 8000
ENV MATTER_HUB_DB=/app/data/matter-hub.db
CMD ["uvicorn", "matter_hub.webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
