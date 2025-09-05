# Dockerfile
FROM python:3.11-slim

# System deps (optional, useful for some libs)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Create user (non-root)
RUN useradd -m appuser
WORKDIR /app

# Install Python deps
# Copy your files — if you have a requirements.txt use that; else use pyproject
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the actual app
COPY . /app

# Switch to non-root
USER appuser

# Expose internal app port
EXPOSE 8000

# Start Gunicorn with Uvicorn workers
# Replace "app.main:app" with your module:app path
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "main:app"]