# Set the base image to the official Python image
FROM python:3.10-slim-buster

# Install the necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY app.py .

# Set the environment variables
ENV FLASK_APP=app
ENV AWS_ACCESS_KEY_ID=default
ENV AWS_SECRET_ACCESS_KEY=default
ENV AWS_REGION=default
ENV QUEUE_URL=default

# Run the Python script with Celery
CMD ["flask", "run", "--reload"]