FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -r secflow && useradd -r -g secflow secflow

WORKDIR /app

COPY requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.lock

COPY . /app/
RUN chown -R secflow:secflow /app

USER secflow

# HEALTHCHECK deferred to Phase 2
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
