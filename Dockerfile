FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files & run migrations during build or entrypoint
RUN python manage.py collectstatic --noinput || true

EXPOSE 8080

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_lessons && gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 config.wsgi:application"]
