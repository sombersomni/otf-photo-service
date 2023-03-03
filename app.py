from io import BytesIO
import boto3
import psd_tools
from PIL import Image

from flask import Flask, jsonify

app = Flask(__name__)

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
)

# Parameters for downloading the PSD file
bucket_name = 'otfnbagraphics'
key = 'periodgamescores/nba-quarter-1080x1920.psd'
key_2 = "common/assets/teams/icons/atlanta-hawks.png"

@app.route('/')
def index():
    # Download the PSD file from S3
    data = s3.get_object(Bucket=bucket_name, Key=key)['Body'].read()
    image_data = s3.get_object(Bucket=bucket_name, Key=key_2)['Body'].read()
    # Parse the PSD file with psd_tools
    psd_file = psd_tools.PSDImage.open(BytesIO(data))
    # Get the layer information from the PSD file
    def get_layers(doc):
        layer_data = []
        for layer in doc.descendants():
            if layer.is_group():
                layer_data + get_layers(layer)
            else:
                layer_data.append(layer)
        return layer_data

    layers = get_layers(psd_file)
    layer_to_replace = [layer for layer in layers if layer.name == 'Away Team Logo' if layer.is_visible()][-1]

    # Open the replacement image with PIL
    replacement_image = Image.open(BytesIO(image_data))

    # Crop the replacement image to fit within the bounds of the layer
    width_ratio = replacement_image.width / layer_to_replace.width
    height_ratio = replacement_image.height / layer_to_replace.height
    if width_ratio > height_ratio:
        new_height = layer_to_replace.height
        new_width = int(replacement_image.width * (new_height / replacement_image.height))
    else:
        new_width = layer_to_replace.width
        new_height = int(replacement_image.height * (new_width / replacement_image.width))
    left = (new_width - layer_to_replace.width) / 2
    top = (new_height - layer_to_replace.height) / 2
    right = left + layer_to_replace.width
    bottom = top + layer_to_replace.height
    cropped_image = replacement_image.crop((left, top, right, bottom))

    # Replace the layer's image data with the cropped replacement image
    layer_to_replace.topil().paste(cropped_image, (0, 0))
    layer_to_replace.image_data = layer_to_replace.topil()

    text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
    # Change text
    for text_layer in text_layers:
        if text_layer.name in ['Away Score', 'Home Score']:
            text_layer.text.value = '55'

    # Save the modified PSD file to a buffer or file
    # output_buffer = BytesIO()
    # psd_file.save(output_buffer)
    psd_file.save('output.psd')

    # Save the merged image as a PNG file
    return jsonify([layer.name for layer in psd_file])



if __name__ == '__main__':
  app.run()
