FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -r secflow && useradd -r -g secflow secflow

WORKDIR /app

COPY requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.lock

COPY . /app/
RUN chown -R secflow:secflow /app

ENV SECFLOW_WORKSPACE_ROOT=/var/lib/secflow/workspaces

USER secflow

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode() == 200 else 1)"
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
