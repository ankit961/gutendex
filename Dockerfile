# ---- Base image with Python ----
FROM python:3.9-slim

# ---- System dependencies ----
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# ---- Set workdir ----
WORKDIR /app

# ---- Copy requirements first for caching ----
COPY requirements.txt .

# ---- Install Python dependencies ----
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ---- Copy app source code ----
COPY . .

# ---- Expose FastAPI port ----
EXPOSE 8000

# ---- Entrypoint ----
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
