FROM python:3.11-slim

WORKDIR /app

# Pre-install CPU-only PyTorch to avoid downloading 2 GB of unnecessary CUDA packages.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download en_core_web_sm

# ── Pre-download the embedding model at build time ──────────────────────────
# This bakes the model into the image so containers never need internet access
# at runtime. Without this, sentence-transformers retries huggingface.co 5
# times (exponential backoff ~31 s) on every cold start, causing ECONNRESET.
ENV SENTENCE_TRANSFORMERS_HOME=/app/model_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Tell HuggingFace Hub to skip ALL network calls at runtime
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
