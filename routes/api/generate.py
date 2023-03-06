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
        data = s3.get_object(Bucket=bucket_name, Key=key)['Body'].read()
        # Parse the PSD file with psd_tools

        psd_file = psd_tools.PSDImage.open(BytesIO(data))
        psd_file.topil().save('data/input.png')
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

        # # do initial edit using photohsop and save psd
        # text_layer = [layer for layer in layers if layer.name == 'Away Score'][-1]
        # access_token = "eyJhbGciOiJSUzI1NiIsIng1dSI6Imltc19uYTEta2V5LWF0LTEuY2VyIiwia2lkIjoiaW1zX25hMS1rZXktYXQtMSIsIml0dCI6ImF0In0.eyJpZCI6IjE2NzgwNzc1OTk1NjVfZGVjNTIxY2ItMGUyZC00MmE3LTlhN2MtM2FmMDRiNmNjMzRiX3VlMSIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiIwZmRkYzhkNDcyNjc0NzQ2YjdmNzhiNGM1NDRiMDlhNCIsInVzZXJfaWQiOiI3MkE4Mjk1MTYzRjhDQjdDMEE0OTVDRjNAdGVjaGFjY3QuYWRvYmUuY29tIiwiYXMiOiJpbXMtbmExIiwiYWFfaWQiOiI3MkE4Mjk1MTYzRjhDQjdDMEE0OTVDRjNAdGVjaGFjY3QuYWRvYmUuY29tIiwiY3RwIjozLCJmZyI6IlhJQUxQTUpXRlBGNUlONEtFTVFWWkhRQVpVPT09PT09IiwibW9pIjoiOTU3NGM5MTkiLCJleHBpcmVzX2luIjoiODY0MDAwMDAiLCJzY29wZSI6Im9wZW5pZCxBZG9iZUlELHJlYWRfb3JnYW5pemF0aW9ucyIsImNyZWF0ZWRfYXQiOiIxNjc4MDc3NTk5NTY1In0.GI145SUmO25DZBT8H8avcXU7TDnegz4nviMny9dfoz3XCwKqEG7pbV-FlSoVFabIk-M8rqzbMYCaZx3xlkytt4aGDAxIEUvwg7GF8snWGQoVB2F2GTH_EFrgwqo0mLQ_z6XqV3fEOGH4lnaiJp9rLfQnWBBDeE3sTR0oT5baaXWZJsPbTLEvwmsGhSfaEdsDhWRjvHVdtdNdQkz1gOugTWVPV64co4foaH6OvE702B4rnpQgtZ4JV4xPA7N57RWDdYb6oiLxOge20ZIOiS3PzL4q7P-6vMOcIm2DIArBLgtRHMCRWHhz5s6oUkLRm1ychxAFV1V49-LmGlrlWHKsqA"
        # # access_token = await get_access_token(http_session)
        signed_urls = await asyncio.gather(
            *([
                create_presigned_url(s3, bucket_name, key, title, command='get_object', method='GET')
                for title, key in [

                    ("fonts", "periodgamescores/Druk-Heavy-Trial.otf"),
                    ("inputs", "periodgamescores/nba-quarter-1080x1920.psd"),
                ]
            ]
              + [
                create_presigned_url(s3, bucket_name, key, title, command='put_object', method='PUT')
                for title, key in [
                    ("outputs", "periodgamescores/final_generation.png"),
                ]
            ]),
          return_exceptions=True
        )
        print(signed_urls)
        # print('--------------')
        # payload = {
        #     "inputs": [{
        #         "href": [signed_url for title, signed_url in signed_urls if title == "inputs"][-1],
        #         "storage": "external"
        #     }],
        #     "options": {
        #         "fonts": [
        #             {
        #                 "href": signed_url,
        #                 "storage": "external",
        #             }
        #             for title, signed_url in signed_urls if title == "fonts"
        #         ],
        #         "layers": [
        #             {
        #                 "edit": {},
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
        #             "type": "image/png",
        #         }
        #         for title, signed_url in signed_urls if title == "outputs"
        #     ]
        # }
        # print(payload)
        # await psd_edit(http_session, access_token, payload)
        
        # text_layers = [layer for layer in layers if isinstance(layer, psd_tools.api.layers.Layer) and layer.kind == 'type']
        # # Change text
        # for text_layer in text_layers:
        #     if text_layer.name in ['Away Score', 'Home Score']:
        #         print(text_layer)
        #         print(text_layer.text)
        # fontfile = s3.get_object(Bucket=bucket_name, Key='periodgamescores/Druk-Medium-Trial.otf')['Body'].read()
        # text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
        # print(text_layer.resource_dict)
        # print('--------------------')
        # print(text_layer.engine_dict)
        # print(psd_file.size, text_layer.width, text_layer.height)
        # # Extract the font information from the text layer
        # fill_color = text_layer.resource_dict.get('FontSet', [{}])[0].get('FillColor', (255, 255, 255, 255))
        # font = ImageFont.truetype(BytesIO(fontfile), int(87))
        # new_text = 'END 3 Can I be Longer'
        # text_width, text_height = font.getsize(new_text)
        # # Create a blank image with an alpha channel
        # print(text_width, text_height)
        # text_area = text_width * text_height
        # layer_area = text_layer.width * text_layer.height
        # text_image = Image.new('RGBA', (text_width + 5, text_height + 5), (0, 0, 0, 0))


        # print(text_area, layer_area, layer_area / text_area)
        # # Draw the text onto the image
        # draw = ImageDraw.Draw(text_image)
        # draw.text((0, 0), new_text, font=font, fill=fill_color, align='center', direction=None)
        # # text_image = text_image.transform(text_layer.size, Image.AFFINE, (1, 0, 0, 0.25, 1, 0))
        # # Combine all layer images into a single PIL image
        # text_images = (Title_Image_Zip('Period Title', t) for t in [text_image])
        images_to_process = resized_images  
        layer_images = bulk_layer_composites(layers, images_to_process, psd_file.size)

        merged_image = Image.new(mode='RGBA', size=psd_file.size, color=(0, 0, 0, 0))
        for layer_image in layer_images:
            merged_image.alpha_composite(layer_image)

        # Save the merged image as a PNG file
        merged_image.save('data/output.png', format='PNG')

        presigned_post = await asyncio.to_thread(
          s3.generate_presigned_post,
          bucket_name,
          "periodgamescores/merged-img.png",
          Fields=None,
          Conditions=None,
          ExpiresIn=3600
        )
        print(presigned_post.get('fields').items())
        send_url = f"{presigned_post.get('url')}{presigned_post.get('fields', {}).get('key')}?{'&'.join(k+'='+v for k, v in presigned_post.get('fields', {}).items() if k != 'key')}"
        print(presigned_post, send_url)
        buffer = BytesIO()
        merged_image.save(buffer, format='PNG')
        image_bytes= buffer.getvalue()
        file = {'file': image_bytes}
        requests.post(
            presigned_post.get('url'),
            data=presigned_post.get('fields'),
            files=file
        )
    except Exception as e:
        print(e)
        await http_session.close()
        return jsonify({ "ok": False })
    finally:
        await http_session.close()
    return jsonify([layer.name for layer in psd_file])
