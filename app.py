from io import BytesIO
import boto3
import psd_tools
from PIL import Image
from flask import Flask, jsonify, request

from helpers.psd_layers import get_layers
from helpers.buckets import get_images_from_s3_keys

app = Flask(__name__)

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
)

# Parameters for downloading the PSD file
bucket_name = 'otfnbagraphics'
key = 'periodgamescores/nba-quarter-1080x1920.psd'
key_2 = "common/assets/teams/icons/atlanta-hawks.png"

event_map = {
    "Away Team Logo": {
        "value": "common/assets/teams/icons/{}.png",
        "eventKey": "awayTeam"
    },
    "Home Team Logo": {
        "value": "common/assets/teams/icons/{}.png",
        "eventKey": "homeTeam"
    },
    "Getty Image": {
        "value":  "periodgamescores/GettyImages-1465156344.jpg",
        "eventKey": None
    }
}

@app.route('/')
def index():
    return (
        "Welcome to the Photo Processing Service\n"
        + "Here are the available endpoints:\n"
        + "/generate  -  creates photos based on event taken in\n"
    )

@app.route('/generate', methods=['POST'])
async def generate():
    body: dict = request.get_json()
    if not all(key in ['awayTeam', 'homeTeam'] for key in body.keys()):
        return jsonify({ "err": "Invalid event keys"})

    # Download the PSD file from S3
    data = s3.get_object(Bucket=bucket_name, Key=key)['Body'].read()
    # Parse the PSD file with psd_tools

    psd_file = psd_tools.PSDImage.open(BytesIO(data))
    # Get the layer information from the PSD file
    layers = get_layers(psd_file)

    layers_to_replace = [layer for layer in layers if layer.name in event_map and layer.is_visible()]
    print(layers_to_replace)
    bucket_key_title_zipped = (
        (
            (
                event_map.get(layer.name).get('value')
                if 'Getty' in layer.name
                else event_map.get(layer.name).get('value').format(body.get(key))
            ),
            layer.name
        ) for key, layer in 
        (
            (event_map.get(layer.name).get('eventKey'), layer) for layer in layers_to_replace
            if event_map.get(layer.name, {}).get('value') is not None
        )
    )
    replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
    print([img.filename for img in replacement_images])
    # # Resize the replacement image to fit within the bounds of the layer
    # width_ratio = replacement_image.width / layer_to_replace.width
    # height_ratio = replacement_image.height / layer_to_replace.height
    # if width_ratio > height_ratio:
    #     new_width = layer_to_replace.width
    #     new_height = int(replacement_image.height * (new_width / replacement_image.width))
    # else:
    #     new_height = layer_to_replace.height
    #     new_width = int(replacement_image.width * (new_height / replacement_image.height))
    # resized_image = replacement_image.resize((new_width, new_height))

    # # Replace the layer's image data with the cropped replacement image
    # layer_to_replace.topil().paste(resized_image, (0, 0))

    # text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
    # # Change text
    # for text_layer in text_layers:
    #     if text_layer.name in ['Away Score', 'Home Score']:
    #         print(text_layer)
    #         print(text_layer.text)

    # # Save the modified PSD file to a buffer or file
    # # output_buffer = BytesIO()
    # # psd_file.save(output_buffer)
    # # psd_file.save('output.psd')

    # # Find all visible layers
    # visible_layers = [layer for layer in get_layers(psd_file) if layer.is_visible()]

    # # Composite each visible layer into a separate PIL image
    # layer_images = []
    # print(psd_file.size)
    # for i, layer in enumerate(visible_layers):
    #     print(layer.name, layer.kind)
    #     if 'Vignette' in layer.name:
    #         print(layer, layer.has_clip_layers(), layer.has_effects(), layer.has_mask(), layer.has_pixels())

    #     else:
    #         layer_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
    #         layer_data = layer.composite()
    #         layer_image.paste(layer_data, box=layer.bbox[:2], mask=layer_data)
    #         layer_images.append(layer_image)

    # # Combine all layer images into a single PIL image
    # merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
    # for layer_image in layer_images[::]:
    #     merged_image.alpha_composite(layer_image)

    # # Save the merged image as a PNG file
    # merged_image.save('output.png', format='PNG')

    # Save the merged image as a PNG file
    return jsonify([layer.name for layer in psd_file])

if __name__ == '__main__':
  app.run(debug=True)
