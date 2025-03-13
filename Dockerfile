FROM python:3.9-slim
WORKDIR /app
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# Install Python dependencies
COPY requirements.txt .
# Fix numpy compatibility issues first
RUN pip install --no-cache-dir numpy==1.23.5
RUN pip install --no-cache-dir -r requirements.txt
# Download spaCy model with no-deps flag to prevent reinstalling packages
RUN python -m spacy download en_core_web_sm --no-deps
# Copy project
COPY . .
# Expose port
EXPOSE 8000
# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser
# Run the application
CMD ["python", "run.py"]