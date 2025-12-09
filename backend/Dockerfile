# NimbusFlags/backend/Dockerfile

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg / Postgres
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the whole project into the image
COPY . .

# Make sure Python can import "backend" as a package
ENV PYTHONPATH=/app/backend

# Run migrations then start the app
CMD ["sh", "-c", "alembic -c /app/alembic.ini upgrade head && python backend/app.py"]
