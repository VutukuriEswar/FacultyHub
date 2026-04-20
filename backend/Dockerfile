# Use Python 3.9 slim as base
FROM python:3.9-slim

# Install system dependencies for Chrome/Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    --no-install-recommends \
    && mkdir -p /etc/apt/keyrings \
    && curl -sSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*


# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download NLTK data
RUN python -m nltk.downloader punkt stopwords punkt_tab

# Pre-download HuggingFace models so they're cached in the image
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; print('Caching all-MiniLM-L6-v2...'); SentenceTransformer('all-MiniLM-L6-v2'); print('Caching cross-encoder/ms-marco-MiniLM-L-6-v2...'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512); print('Models cached.')"

# Copy the rest of the backend files
COPY . .

# Expose the default port (Render will override this with the PORT env var)
EXPOSE 8000

# Healthcheck to verify the app is ready
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=120s \
  CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1


# Start the application using the Python script which handles the port correctly
CMD ["python", "server.py"]
