import re
import aiohttp
import asyncio
from io import BytesIO
import boto3
import psd_tools
import requests
from PIL import Image, ImageFont, ImageDraw
from flask import g, jsonify, request
from constants import Key_Title_Zip, Title_Image_Zip
from helpers.photoshop import get_access_token, psd_edit
from itertools import chain
from helpers.psd_layers import bulk_layer_composites, bulk_resize_images, flatten_layers
from helpers.buckets import (
    create_presigned_post_for_psd_layer,
    get_images_from_s3_keys,
    create_presigned_url_for_psd_layer
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
        "value":  "periodgamescores/cropped_img.png",
        "eventKey": None
    },
    "Period Title": {
        "value":  "END 3",
        "eventKey": "period"
    }
}

async def generate_controller(s3, http_session):
    try:
        body: dict = request.get_json()
        if (
            not all(key in ['awayTeam', 'homeTeam', 'awayScore', 'homeScore'] for key in body.keys())
        ):
            return jsonify(error="Request body is invalid"), 400

        # Download the PSD file from S3
        psd_object = await asyncio.to_thread(s3.get_object, Bucket=bucket_name, Key=key)
        data = psd_object['Body'].read()
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

        replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
        resized_images = bulk_resize_images(replacement_images, replacement_layer_map)

        # images_to_process = resized_images  
        # layer_images = bulk_layer_composites(layers, images_to_process, psd_file.size)

        # merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
        # for layer_image in layer_images:
        #     merged_image.alpha_composite(layer_image)

        # # Save the merged image as a PNG file
        # merged_image.save('data/output.png', format='PNG')

        # buffer = BytesIO()
        # merged_image.save(buffer, format='PNG')
        # image_bytes= buffer.getvalue()
        # file = {'file': image_bytes}
        # await asyncio.to_thread(
        #     requests.post,
        #     presigned_post.get('url'),
        #     data=presigned_post.get('fields'),
        #     files=file
        # )
    except Exception as e:
        print(e)
        await http_session.close()
        return jsonify({ "ok": False })
    finally:
        await http_session.close()
    return jsonify([layer.name for layer in psd_file])
