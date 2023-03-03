from io import BytesIO
import boto3
import psd_tools

from flask import Flask, jsonify

app = Flask(__name__)

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id='your-access-key-id',
    aws_secret_access_key='your-secret-access-key'
)

# Parameters for downloading the PSD file
bucket_name = 'your-bucket-name'
key = 'path/to/your/psd/file.psd'

@app.route('/')
def index():
    # Download the PSD file from S3
    data = s3.get_object(Bucket=bucket_name, Key=key)['Body'].read()

    # Parse the PSD file with psd_tools
    psd_file = psd_tools.PSDImage.open(BytesIO(data))

    # Get the layer information from the PSD file
    layer_data = []
    for layer in psd_file.layers:
        layer_data.append({
            'name': layer.name,
            'width': layer.width,
            'height': layer.height,
            'opacity': layer.opacity,
            'blend_mode': layer.blending_mode,
            'is_visible': layer.visible,
            'image_data': layer.topil()
        })

    # Return the layer information as JSON
    return jsonify(layer_data)


if __name__ == '__main__':
  app.run()
