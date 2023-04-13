import re
import aiohttp
import asyncio
import functools
import contextvars
from io import BytesIO
import boto3
import psd_tools
from PIL import Image, ImageFont, ImageDraw
from flask import g, jsonify, request
from constants import Key_Title_Zip, Key_Font_Zip
from itertools import chain
from helpers.psd_layers import (
    bulk_layer_composites,
    bulk_replicate_text,
    bulk_resize_images,
    flatten_layers
)
from helpers.buckets import (
    create_presigned_post_for_psd_layer,
    get_images_from_s3_keys,
    get_fonts_from_s3_keys,
    create_presigned_url_for_psd_layer
)

# Parameters for downloading the PSD file
bucket_name = 'otfnbagraphics'
key = 'periodgamescores/nba-quarter-1080x1920.psd'
key_2 = "common/assets/teams/icons/atlanta-hawks.png"

event_map = {
    "Away Team Logo": {
        "value": "common/assets/teams/icons/{}.png",
        "eventKey": "awayTeam",
        "type": "image"
    },
    "Home Team Logo": {
        "value": "common/assets/teams/icons/{}.png",
        "eventKey": "homeTeam",
        "type": "image"
    },
    "Getty Image": {
        "value":  "periodgamescores/cropped_img.png",
        "eventKey": None,
        "type": "image"
    },
    "Period Title": {
        "eventKey": "period",
        "type": "text"
    },
    "Away Score": {
        "eventKey": "awayScore",
        "type": "text"
    },
    "Home Score": {
        "eventKey": "homeScore",
        "type": "text"
    },
    "Fonts": ["Druk-Heavy", "Druk-Medium"]
}

async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

async def generate_controller(s3, http_session):
    try:
        body: dict = request.get_json()
        if (
            not all(key in ['awayTeam', 'homeTeam', 'awayScore', 'homeScore', 'period'] for key in body.keys())
        ):
            return jsonify(error="Request body is invalid"), 400

        # Download the PSD file from S3
        print('Retrieving PSD')
        psd_object = await to_thread(s3.get_object, Bucket=bucket_name, Key=key)
        data = psd_object['Body'].read()
        # Parse the PSD file with psd_tools
        print('Open PSD')
        psd_file = psd_tools.PSDImage.open(BytesIO(data))
        # Get the layer information from the PSD file
        layers = list(flatten_layers(psd_file))
        print('Create layers for later image reconstruction')
        layers_to_replace = [
            layer for layer in layers
            if layer.name in event_map
            and layer.is_visible()
        ]
        image_layers_to_replace = [
            layer for layer in layers_to_replace
            if event_map.get(layer.name, {}).get('type') == 'image'
        ]
        image_replacement_layer_map = {layer.name: layer for layer in image_layers_to_replace}
        text_layers_to_replace = [
            layer for layer in layers_to_replace
            if layer.kind == 'type'
            and event_map.get(layer.name, {}).get('type') == 'text'
        ]
        print('Bucket Key combination')
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
                (event_map.get(layer.name).get('eventKey'), layer) for layer in image_layers_to_replace
                if event_map.get(layer.name, {}).get('value') is not None
            )
        )
        print('Retrieve s3 images')
        replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
        print('Crop and resize images')
        resized_images = bulk_resize_images(replacement_images, image_replacement_layer_map)

        # get fonts and set text images
        # grabs font from common assets in bucket
        print('Key Font Zip construction')
        fonts = (Key_Font_Zip(f"common/assets/fonts/{font}.otf", font) for font in event_map.get('Fonts', []))
        print('Retrieve s3 fonts')
        font_types_zipped = await get_fonts_from_s3_keys(s3, bucket_name, fonts)
        font_type_map = {title: font for title, font in font_types_zipped}
        text_value_map = {
            key: str(body[value['eventKey']]) for key, value in event_map.items()
            if key != 'Fonts'
            and value.get('type') == 'text'
            and body.get(value['eventKey']) is not None
        }
        print('Replicate text as images')
        replicated_text_images = bulk_replicate_text(text_layers_to_replace, psd_file.size, font_type_map, text_value_map)
        for title, image in replicated_text_images:
            image.save(f"data/{title}.png", format='PNG')
        # chain images and fonts together for processing
        # images_to_process = chain(resized_images, replicated_text_images)

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
