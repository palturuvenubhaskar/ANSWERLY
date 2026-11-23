FROM python:3.12-slim

# System dependencies for PyMuPDF, python-docx, reportlab, and tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and Alembic migrations
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini

ENV PYTHONPATH=/app
ENV LOCAL_STORAGE_PATH=/app/storage
RUN mkdir -p /app/storage

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000"]
