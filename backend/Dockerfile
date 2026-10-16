FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Offline Hindi + English OCR; no hosted OCR credentials or network service required at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng ffmpeg espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Verify that the image actually contains the offline audio tools and Hindi TTS voice.
RUN command -v ffmpeg >/dev/null && command -v espeak-ng >/dev/null \
    && tesseract --list-langs 2>/dev/null | grep -Fxq hin \
    && espeak-ng --stdout -v hi "नमस्ते किसान" > /tmp/saathi-hi.wav \
    && test "$(head -c 4 /tmp/saathi-hi.wav)" = "RIFF" \
    && rm /tmp/saathi-hi.wav
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt
COPY app ./app
COPY scripts/smoke_local_ocr.py /tmp/smoke_local_ocr.py
RUN python /tmp/smoke_local_ocr.py

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
