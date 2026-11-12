# Build context is the repository root (see docker-compose.yml) so the drumscript package can be copied in.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    TORCH_HOME=/models/torch NUMBA_CACHE_DIR=/tmp/numba

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch (small wheels, no CUDA)
RUN pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu

COPY ml_worker/requirements.txt .
RUN pip install -r requirements.txt

COPY pyproject.toml /src/pyproject.toml
COPY drumscript /src/drumscript
RUN pip install --no-deps /src

COPY ml_worker/worker.py .
RUN mkdir -p /models /data

# --pool=solo: one job at a time in the main process (PyTorch already uses all cores)
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--pool=solo", "--queues=transcription"]
