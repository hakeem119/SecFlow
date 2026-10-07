FROM python:3.12.15-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -r secflow && useradd -r -g secflow secflow

WORKDIR /app

COPY requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.lock

# --- M1: git ---
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git --version
# ---------------

# --- M2: tools ---
# Install Syft
# Checksum from https://github.com/anchore/syft/releases/download/v1.54.1/syft_1.54.1_checksums.txt
ARG SYFT_VERSION="1.54.1"
ARG SYFT_CHECKSUM="c069905b391cc4c20a5ba65ad5c10be2a7ba074f8ea6ad203e24d14e303dad47"
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sSfL -o syft.tar.gz "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_linux_amd64.tar.gz" \
    && echo "${SYFT_CHECKSUM}  syft.tar.gz" | sha256sum -c - \
    && tar -xzf syft.tar.gz -C /usr/local/bin syft \
    && rm syft.tar.gz \
    && echo "check-for-app-update: false" > /etc/syft.yaml \
    && chmod 644 /etc/syft.yaml

# Install scc
ARG SCC_VERSION="4.1.0"
RUN curl -sSfL -o scc.tar.gz "https://github.com/boyter/scc/releases/download/v${SCC_VERSION}/scc_Linux_x86_64.tar.gz" \
    && tar -xzf scc.tar.gz -C /usr/local/bin scc \
    && rm scc.tar.gz

# Install Semgrep and detect-secrets
RUN pip install --no-cache-dir semgrep==1.179.0 detect-secrets==1.5.0 \
    && mkdir -p /opt/secflow/rules/semgrep \
    && echo "rules:\n  - id: dummy-rule\n    pattern: TODO\n    message: 'TODO found'\n    languages: [generic]\n    severity: WARNING" > /opt/secflow/rules/semgrep/dummy.yaml \
    && chown -R root:root /opt/secflow/rules \
    && chmod -R 755 /opt/secflow/rules \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
# -----------------

COPY . /app/
RUN chown -R secflow:secflow /app

ENV SECFLOW_WORKSPACE_ROOT=/var/lib/secflow/workspaces
RUN mkdir -p /var/lib/secflow/workspaces \
    && chown secflow:secflow /var/lib/secflow/workspaces \
    && chmod 700 /var/lib/secflow/workspaces

USER secflow

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode() == 200 else 1)"
CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
