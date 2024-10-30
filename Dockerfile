# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV API_HOST=0.0.0.0
ENV SPREADSHEET_ID=1niDCOegC7SKkqYjCDhKkia3Oc6D-5bvUIHKDnNMG8YE
ENV SERVICE_ACCOUNT=70295468269-compute@developer.gserviceaccount.com
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json

# Install system dependencies and fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    xvfb \
    xauth \
    libxrender1 \
    libjpeg-dev \
    fontconfig \
    libfontconfig1 \
    wkhtmltopdf \
    curl \
    fonts-roboto && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy fonts (updated path)
COPY fonts /app/fonts
RUN fc-cache -f -v

# Copy application files
COPY . .

# Create start script
RUN echo '#!/bin/bash\n\
echo "Starting Production FastAPI application..."\n\
exec gunicorn main:app \
--workers 2 \
--worker-class uvicorn.workers.UvicornWorker \
--bind 0.0.0.0:$PORT \
--timeout 120 \
--access-logfile - \
--error-logfile -' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE $PORT

# Start the application
CMD ["/app/start.sh"]