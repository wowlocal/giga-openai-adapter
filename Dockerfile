FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy certificate files
COPY russian_trusted_root_ca.cer .
COPY proxyman.pem .

# Copy .env file
COPY .env .

# Copy application code
COPY app/ app/
COPY run.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 3001

# Command to run the application
CMD ["python", "run.py"]