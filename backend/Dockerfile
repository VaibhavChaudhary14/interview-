FROM python:3.11-slim

WORKDIR /app

# Pre-install CPU-only PyTorch to avoid downloading 2 GB of unnecessary CUDA packages.
# This prevents network timeouts and speeds up building the container significantly.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
