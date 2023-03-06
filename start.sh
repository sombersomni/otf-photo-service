#!/bin/bash

# Load the environment variables from the .env file
set -a
[ -f .env ] && . .env
set +a

# Start the Docker container with the environment variables
docker build \
  --build-arg FLASK_RUN_PORT=$FLASK_RUN_PORT \
  --build-arg FLASK_DEBUG=$FLASK_DEBUG \
  --build-arg AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --build-arg AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  --build-arg AWS_REGION=$AWS_REGION \
  -t otf-photo-service \
  .