import boto3
import os
from flask import Flask, g

config = {
  "retries": {
    "mode": "standard"
  }
}

def s3_middleware(app):
    def before_request():
        # Initialize s3 client for AWS
        g.s3_client = boto3.client(
          's3',
          region_name=os.environ.get('AWS_REGION'),
          aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
          aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY_ID'),
          config=config
        )
    app.before_request(before_request)
