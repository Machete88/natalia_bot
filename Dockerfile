# natalia_bot - Docker Image
FROM python:3.11-slim

# Systempakete fuer OCR (Tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-rus \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhaengigkeiten zuerst (Cache-Layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code
COPY . .

# Verzeichnisse anlegen
RUN mkdir -p data logs media/cache media/audio media/homework media/stickers content

# Kein root
RUN useradd -m botuser && chown -R botuser /app
USER botuser

# .env wird zur Laufzeit per -v oder --env-file eingebunden
CMD ["python", "-m", "app.main"]
