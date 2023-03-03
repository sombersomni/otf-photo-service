# Set the base image to the official Python image
FROM python:3.9-slim-buster

# Install the necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY app.py .

# Set the environment variables
ENV AWS_ACCESS_KEY_ID=<your_access_key>
ENV AWS_SECRET_ACCESS_KEY=<your_secret_key>
ENV AWS_REGION=<your_region>
ENV QUEUE_URL=<your_queue_url>
ENV CELERY_BROKER_URL=redis://redis:6379/0

# Run the Python script with Celery
CMD ["celery", "-A", "app", "worker", "--loglevel=info"]