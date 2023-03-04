import re
import aiohttp
import asyncio
from io import BytesIO
import boto3
import psd_tools
from PIL import Image, ImageFont, ImageDraw
from flask import g, jsonify, request
from constants import Key_Title_Zip
from helpers.photoshop import get_access_token, psd_edit

from helpers.psd_layers import bulk_layer_composites, bulk_resize_images, flatten_layers
from helpers.buckets import create_presigned_post, get_images_from_s3_keys, create_presigned_url

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

async def generate_controller(s3, http_session):
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
    # # do initial edit using photohsop and save psd
    # text_layer = [layer for layer in layers if layer.name == 'Away Score'][-1]
    # access_token = await get_access_token(http_session)
    # signed_urls = await asyncio.gather(
    #     *([
    #         create_presigned_url(s3, bucket_name, key, title, method='GET', command='get_object')
    #         for title, key in [

    #             ("fonts", "periodgamescores/Druk-Heavy.ttf"),
    #             ("inputs", "periodgamescores/nba-quarter-1080x1920.psd"),
    #         ]
    #     ]
    #       + [
    #         create_presigned_url(s3, bucket_name, key, title, method='PUT', command='put_object')
    #         for title, key in [
    #             ("outputs", f"final.psd"),
    #         ]
    #     ]),
    #   return_exceptions=True
    # )
    # print('--------------')
    # print(text_layer.resource_dict)
    # payload = {
    #     "inputs": [{
    #         "href": [signed_url for title, signed_url in signed_urls if title == "inputs"][-1],
    #         "storage": "external"
    #     }],
    #     "options": {
    #         "layers": [
    #             {
    #                 "name": text_layer.name,
    #                 "text": {
    #                     "content": "44"
    #                 }
    #             }
    #         ]
    #     },
    #     "outputs": [
    #         {
    #             "href": signed_url,
    #             "storage": "external",
    #             "type": "vnd.adobe.photoshop",
    #         }
    #         for title, signed_url in signed_urls if title == "outputs"
    #     ]
    # }
    # print(payload)
    # await psd_edit(http_session, access_token, payload)
    #
    # replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
    # resized_images = bulk_resize_images(replacement_images, replacement_layer_map)


    # text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
    # # Change text
    # for text_layer in text_layers:
    #     if text_layer.name in ['Away Score', 'Home Score']:
    #         print(text_layer)
    #         print(text_layer.text)
    # fontfile = s3.get_object(Bucket=bucket_name, Key='periodgamescores/Druk-Heavy.ttf')['Body'].read()
    # text_layer = [layer for layer in layers if layer.name == 'Away Score'][-1]
    # text_layer.topil().show()
    # print(text_layer.resource_dict)
    # print(text_layer.engine_dict)
    # print(psd_file.size[0] / text_layer.width)
    # # Extract the font information from the text layer
    # font_family = text_layer.resource_dict.get('FontSet', [{}])[0].get('Name', 'Helvetica')
    # fill_color = text_layer.resource_dict.get('FontSet', [{}])[0].get('FillColor', (255, 255, 255, 255))
    # font_size = text_layer.width
    # font = ImageFont.truetype(BytesIO(fontfile), font_size)

    # # Create a blank image with an alpha channel
    # text_image = Image.new('RGBA', (text_layer.width, text_layer.height), (0, 0, 0, 0))
    # print(text_layer.left, text_layer.right)
    # # Draw the text onto the image
    # draw = ImageDraw.Draw(text_image)
    # draw.text((0, 0), '127', font=font, fill=fill_color, spacing=-1, align='center', direction=None)
    # text_image = text_image.transform(text_layer.size, Image.AFFINE, (1, 0, 0, 0.25, 1, 0))

    # # # Combine all layer images into a single PIL image  
    # layer_images = bulk_layer_composites(layers, resized_images, psd_file.size)

    # merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
    # for layer_image in layer_images:
    #     merged_image.alpha_composite(layer_image)

    # # # Save the merged image as a PNG file
    # merged_image.save('output.png', format='PNG')

    # Save the merged image as a PNG file
    return jsonify([layer.name for layer in psd_file])
