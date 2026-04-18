FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 3001

# Entrypoint: app.serve:app  (no main.py needed)
CMD ["uvicorn", "app.serve:app", "--host", "0.0.0.0", "--port", "8000"]
