FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including MuseScore CLI tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    xvfb \
    wget \
    libopengl0 \
    ca-certificates \
    coreutils \
    build-essential \
    python3-dev \
    pkg-config \
    libfftw3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install MuseScore 3 CLI for .mscx/.mscz export support (ARM64/Apple Silicon)
RUN apt-get update && \
    apt-get install -y musescore3 && \
    ln -s /usr/bin/musescore3 /usr/local/bin/mscore4 && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /app/uploads

# Run Celery worker
CMD ["celery", "-A", "worker", "worker", "--loglevel=info", "--concurrency=1", "--queues=transcription"]