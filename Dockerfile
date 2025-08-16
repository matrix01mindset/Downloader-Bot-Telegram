# Telegram Video Downloader Bot - Secure Dockerfile
# Optimized for Render.com deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies - Force rebuild 2025-08-12
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p temp_downloads logs \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=10000

# Expose port (Render will override this)
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application
# Dockerfile pentru Render deployment
FROM python:3.11-slim

# Setează directorul de lucru
WORKDIR /app

# Copiază requirements.txt și instalează dependențele
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază toate fișierele aplicației
COPY . .

# Expune portul
EXPOSE 10000

# Setează variabilele de mediu
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Rulează aplicația
CMD ["python", "app.py"]