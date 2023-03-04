#!/bin/bash

# Load the environment variables from the .env file
set -a
[ -f .env ] && . .env
set +a

# Start the Docker container with the environment variables
docker run \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_REGION=$AWS_REGION \
  -e QUEUE_URL=$QUEUE_URL \
  -e CELERY_BROKER_URL=$CELERY_BROKER_URL \
  otf