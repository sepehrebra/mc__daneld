FROM python:3.12-slim

# Optional PyPI mirror override (set PIP_INDEX_URL in .env if pypi.org is unreachable)
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install only the dependencies listed in pyproject.toml (the project itself is not installed).
# Copying pyproject.toml alone first keeps this layer cached until dependencies change.
COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY django_backend/ /app/django_backend/
COPY deploy/entrypoint.sh /entrypoint.sh

# Strip possible CRLF endings, make the script executable, create the non-root user and the DB directory
RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod 755 /entrypoint.sh \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data

USER app
WORKDIR /app/django_backend
ENTRYPOINT ["/entrypoint.sh"]