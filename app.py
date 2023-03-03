import aiohttp
from io import BytesIO
import boto3
import psd_tools
from PIL import Image, ImageFont, ImageDraw
from flask import Flask, jsonify, request
from constants import Key_Title_Zip
from helpers.photoshop import poll_request

from helpers.psd_layers import bulk_layer_composites, bulk_resize_images, flatten_layers
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
    layers = list(flatten_layers(psd_file))
    layers_to_replace = [layer for layer in layers if layer.name in event_map and layer.is_visible()]
    replacement_layer_map = {layer.name: layer for layer in layers_to_replace}
    # Get all the bucket keys related to image layers
    bucket_key_title_zipped = (
        Key_Title_Zip(
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
            and any(
                image_format in event_map.get(layer.name, {}).get('value')[-4:]
                for image_format in ['jpg', 'jpeg', 'png']
            )
        )
    )
    #
    # replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
    # resized_images = bulk_resize_images(replacement_images, replacement_layer_map)


    # text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
    # # Change text
    # for text_layer in text_layers:
    #     if text_layer.name in ['Away Score', 'Home Score']:
    #         print(text_layer)
    #         print(text_layer.text)
    fontfile = s3.get_object(Bucket=bucket_name, Key='periodgamescores/Druk-Heavy.ttf')['Body'].read()
    text_layer = [layer for layer in layers if layer.name == 'Away Score'][-1]
    text_layer.topil().show()
    print(text_layer.resource_dict)
    print(text_layer.engine_dict)
    print(psd_file.size[0] / text_layer.width)
    # Extract the font information from the text layer
    font_family = text_layer.resource_dict.get('FontSet', [{}])[0].get('Name', 'Helvetica')
    fill_color = text_layer.resource_dict.get('FontSet', [{}])[0].get('FillColor', (255, 255, 255, 255))
    font_size = text_layer.width
    font = ImageFont.truetype(BytesIO(fontfile), font_size)

    # Create a blank image with an alpha channel
    text_image = Image.new('RGBA', (text_layer.width, text_layer.height), (0, 0, 0, 0))
    print(text_layer.left, text_layer.right)
    # Draw the text onto the image
    draw = ImageDraw.Draw(text_image)
    draw.text((0, 0), '127', font=font, fill=fill_color, spacing=-1, align='center', direction=None)
    text_image = text_image.transform(text_layer.size, Image.AFFINE, (1, 0, 0, 0.25, 1, 0))

    # Save the text image as a PNG file with an alpha channel
    text_image.show()
    # layer_images = bulk_layer_composites(layers, resized_images, psd_file.size)

    # # # Combine all layer images into a single PIL image
    # merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
    # for layer_image in layer_images:
    #     merged_image.alpha_composite(layer_image)

    # # # Save the merged image as a PNG file
    # merged_image.save('output.png', format='PNG')

    # Save the merged image as a PNG file
    return jsonify([layer.name for layer in psd_file])

@app.route('/poll')
async def poll():
    token = ''
    api_key = ''
    headers = {
        "Content-Type": 'application/json',
        "Authorization": f"Bearer {token}",
        "x-api-key": api_key
    }
    payload = {
        'manageFontsMissing': 'fail',
        
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        response = await session.post(
            '',
            data=payload
        )
        if response.status == 200:
            data = await response.json()
            print(data)

    await poll_request('https://dummyjson.com/products')
    return 'ok'

if __name__ == '__main__':
  app.run(debug=True)
