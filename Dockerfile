FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

ENV PATH="${PATH}:${POETRY_VENV}/bin"

WORKDIR /airbyte/integration_code

# Copy poetry files first
COPY pyproject.toml poetry.lock ./

# Install dependencies in the system Python
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy source code
COPY . .

# Install the package itself
RUN poetry install --only main --no-interaction --no-ansi

# Verify installation
RUN poetry run python -c "import airbyte_cdk; print('CDK installed successfully')"

ENV AIRBYTE_ENTRYPOINT="poetry run python /airbyte/integration_code/main.py"
ENTRYPOINT ["poetry", "run", "python", "/airbyte/integration_code/main.py"]

LABEL io.airbyte.version=0.1.0
LABEL io.airbyte.name=airbyte/source-excel-sheets