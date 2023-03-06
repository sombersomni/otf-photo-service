# Set the base image to the official Python image
FROM python:3.10-alpine

# Pass environment variables to the Docker build
ARG FLASK_RUN_PORT=8080
ARG FLASK_DEBUG=0
ARG AWS_ACCESS_KEY_ID=default
ARG AWS_SECRET_ACCESS_KEY=default
ARG AWS_REGION=default

# Set environment variables for the Docker container
ENV FLASK_RUN_PORT=${FLASK_RUN_PORT}
ENV FLASK_DEBUG=${FLASK_DEBUG}
ENV FLASK_APP=app
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_REGION=${AWS_REGION}

# Set the working directory
WORKDIR /app

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY app.py .
COPY constants.py .
COPY lib lib
COPY routes routes
COPY helpers helpers
COPY routes routes
COPY middleware middleware

# Run the Python script with Celery
CMD ["flask", "run", "--reload"]