FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY sql ./sql
COPY dashboard ./dashboard
COPY data ./data
COPY output ./output
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "audit_engine.api:app", "--host", "0.0.0.0", "--port", "8000"]

