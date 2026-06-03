FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/main.py .

# Copy frontend as static files
COPY frontend/index.html ./static/index.html

# Expose port
EXPOSE 8000

# Run FastAPI with Uvicorn (production server)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
