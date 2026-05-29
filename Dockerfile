# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (e.g., for psycopg2 and other native modules)
RUN apt-get update \
    && apt-get install -y gcc libpq-dev tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Download spaCy model required for CV parsing
RUN python -m spacy download en_core_web_sm

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "candidate_filter.wsgi:application"]
