from io import BytesIO
import boto3
import psd_tools
from PIL import Image

from flask import Flask, jsonify, request

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
    return (
        "Welcome to the Photo Processing Service\n"
        + "Here are the available endpoints:\n"
        + "/generate  -  creates photos based on event taken in\n"
    )

@app.route('/generate', methods=['POST'])
def generate():
    print(request.get_json())
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
    print([i.image_data for i in layers if i.__dict__.get('image_data')])
    print(layer_to_replace)
    # Open the replacement image with PIL
    replacement_image = Image.open(BytesIO(image_data))
    # Crop the replacement image to fit within the bounds of the layer
    width_ratio = replacement_image.width / layer_to_replace.width
    height_ratio = replacement_image.height / layer_to_replace.height
    if width_ratio > height_ratio:
        new_width = layer_to_replace.width
        new_height = int(replacement_image.height * (new_width / replacement_image.width))
    else:
        new_height = layer_to_replace.height
        new_width = int(replacement_image.width * (new_height / replacement_image.height))
    resized_image = replacement_image.resize((new_width, new_height))

    # Replace the layer's image data with the cropped replacement image
    layer_to_replace.topil().paste(resized_image, (0, 0))
    psd_file.composite().save('output.png')

    text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
    # Change text
    for text_layer in text_layers:
        if text_layer.name in ['Away Score', 'Home Score']:
            print(text_layer)
            print(text_layer.text)

    # Save the modified PSD file to a buffer or file
    # output_buffer = BytesIO()
    # psd_file.save(output_buffer)
    psd_file.save('output.psd')

    # Save the merged image as a PNG file
    return jsonify([layer.name for layer in psd_file])

if __name__ == '__main__':
  app.run()
