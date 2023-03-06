import re
import aiohttp
import asyncio
from io import BytesIO
import boto3
import psd_tools
from PIL import Image, ImageFont, ImageDraw
from flask import g, jsonify, request
from constants import Key_Title_Zip, Title_Image_Zip
from helpers.photoshop import get_access_token, psd_edit
from itertools import chain
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
        "value":  "periodgamescores/nba.jpg",
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
        # do initial edit using photohsop and save psd
        # text_layer = [layer for layer in layers if layer.name == 'Away Score'][-1]
        # access_token = "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjE2NzgwNTE5MzksImlzcyI6IjcxNEQyNUFDNjNGOENCMzIwQTQ5NUMwN0BBZG9iZU9yZyIsInN1YiI6IjcyQTgyOTUxNjNGOENCN0MwQTQ5NUNGM0B0ZWNoYWNjdC5hZG9iZS5jb20iLCJodHRwczovL2ltcy1uYTEuYWRvYmVsb2dpbi5jb20vcy9lbnRfY2Nhc19zZGsiOnRydWUsImF1ZCI6Imh0dHBzOi8vaW1zLW5hMS5hZG9iZWxvZ2luLmNvbS9jLzBmZGRjOGQ0NzI2NzQ3NDZiN2Y3OGI0YzU0NGIwOWE0In0.bj2FFcxGEBmIQjsj7IJ4BVLdQ62pSSxUCUN_tnYPNESdMH_M9Su2ll3lVm3ntapCGpHKCFzuTYat7vvS14WcQrNmD5sn8Mmzylnl2TQiRVy7rAt1veR9nGZx1Jsj_84M-CGtREvgiuXi8yvtu7lufW5lqcZaTAYpYEPnlIcXWn5BSCXyJL3vy50jB6uUloi9bs3XsoRtIBxiksdhbwiPw4ceFcemVYCb-MYqAAj5VCI05x0DgmUzC8pMK8V1WXdV7n_qpmQA6F12yfm2cP6GTcn9BndLHCva1BZS6ts3j7sgi9A00-JK4H1vQkAYeDu2dV7d8YO0pnNbzRsgk87b7g"
        # # access_token = await get_access_token(http_session)
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
        #     # "options": {
        #     #     "layers": [
        #     #         {
        #     #             "name": text_layer.name,
        #     #             "text": {
        #     #                 "content": "44"
        #     #             }
        #     #         }
        #     #     ]
        #     # },
        #     # "outputs": [
        #     #     {
        #     #         "href": signed_url,
        #     #         "storage": "external",
        #     #         "type": "vnd.adobe.photoshop",
        #     #     }
        #     #     for title, signed_url in signed_urls if title == "outputs"
        #     # ]
        # }
        # print(payload)
        # await psd_edit(http_session, access_token, payload)
        #
        replacement_images = await get_images_from_s3_keys(s3, bucket_name, bucket_key_title_zipped)
        resized_images = bulk_resize_images(replacement_images, replacement_layer_map)


        text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
        # Change text
        for text_layer in text_layers:
            if text_layer.name in ['Away Score', 'Home Score']:
                print(text_layer)
                print(text_layer.text)
        fontfile = s3.get_object(Bucket=bucket_name, Key='periodgamescores/Druk-Medium-Trial.otf')['Body'].read()
        text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
        print(text_layer.resource_dict)
        print('--------------------')
        print(text_layer.engine_dict)
        print(psd_file.size[0] / text_layer.width)
        # Extract the font information from the text layer
        fill_color = text_layer.resource_dict.get('FontSet', [{}])[0].get('FillColor', (255, 255, 255, 255))
        font = ImageFont.truetype(BytesIO(fontfile), 80)
        new_text = 'END 3'
        text_width, text_height = font.getsize(new_text)
        # Create a blank image with an alpha channel
        print(text_width, text_height)
        text_area = text_width * text_height
        layer_area = text_layer.width * text_layer.height
        text_image = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
        text_layer.topil().show()


        print(text_area, layer_area, layer_area / text_area)
        # Draw the text onto the image
        draw = ImageDraw.Draw(text_image)
        draw.text((0, 0), new_text, font=font, fill=fill_color, align='center', direction=None)
        # text_image = text_image.transform(text_layer.size, Image.AFFINE, (1, 0, 0, 0.25, 1, 0))
        text_image.show()
        # Combine all layer images into a single PIL image
        text_images = (Title_Image_Zip('Period Title', t) for t in [text_image])
        images_to_process = chain(resized_images, text_images)  
        layer_images = bulk_layer_composites(layers, images_to_process, psd_file.size)

        merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
        for layer_image in layer_images:
            merged_image.alpha_composite(layer_image)

        # Save the merged image as a PNG file
        merged_image.save('output.png', format='PNG')
    except Exception as e:
        print(e)
        await http_session.close()
        return jsonify({ "ok": False })
    finally:
        await http_session.close()
    return jsonify([layer.name for layer in psd_file])
