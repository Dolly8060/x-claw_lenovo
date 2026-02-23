FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY x_claw /app/x_claw
COPY config /app/config
COPY pyproject.toml README.md /app/

RUN pip install --no-cache-dir uv && uv pip install --system -e .

EXPOSE 8080

CMD ["uvicorn", "x_claw.main:app", "--host", "0.0.0.0", "--port", "8080"]
