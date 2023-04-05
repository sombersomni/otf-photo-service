import asyncio
import functools
import contextvars
from io import BytesIO
from typing import Iterable
from PIL import Image, ImageFont

from constants import Key_Title_Zip, Title_Image_Zip, Key_Font_Zip
from botocore.exceptions import ClientError

async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


async def get_image(client,  bucket_name: str, key_title_zip: Key_Title_Zip):
    key, title = key_title_zip
    if key.endswith('.jpg') or key.endswith('.jpeg') or key.endswith('.png'):
        response = await to_thread(client.get_object, Bucket=bucket_name, Key=key)
        img_bytes = BytesIO(response['Body'].read())
        img = Image.open(img_bytes)
        return Title_Image_Zip(title, img)
    
async def get_font(client,  bucket_name: str, key_font_zip: Key_Font_Zip):
    key, font = key_font_zip
    # Only supports ttf or otf font types
    if font.endswith('.ttf') or font.endswith('.otf'):
        response = await to_thread(client.get_object, Bucket=bucket_name, Key=key)
        font_bytes = BytesIO(response['Body'].read())
        return { font: font_bytes }

async def get_images_from_s3_keys(client, bucket_name: str, key_title_zipped: Iterable[Key_Title_Zip]):
    return await asyncio.gather(
      *[get_image(client, bucket_name, key_title_zip) for key_title_zip in key_title_zipped],
      return_exceptions=True
    )

async def get_fonts_from_s3_keys(client, bucket_name: str, key_font_zipped: Iterable[Key_Font_Zip]):
    return await asyncio.gather(
      *[get_font(client, bucket_name, key_font_zip) for key_font_zip in key_font_zipped],
      return_exceptions=True
    )

async def create_presigned_url_for_psd_layer(
  client,
  bucket_name:str,
  key:str,
  title:str,
  command:str = 'get_object',
  method:str = 'GET',
  expiration=3600
):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param key: string
    :param title: string
    :param command: string
    :param method: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: A tuple which includes the layer title and response. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    try:
        response = await asyncio.to_thread(
          client.generate_presigned_url,
          ClientMethod=command,
          Params={'Bucket': bucket_name, 'Key': key},
          ExpiresIn=expiration,
          HttpMethod=method
        )
    except ClientError as e:
        print(e)
        return None
    else:
      # The response contains the presigned URL
      return (title, response)


async def create_presigned_post_for_psd_layer(
  client,
  bucket_name:str,
  key:str,
  title:str,
  fields=None,
  conditions=None,
  expiration=3600
):
    """Generate a presigned URL S3 POST request to upload a file

    :param bucket_name: string
    :param key: string
    :param title: string
    :param fields: Dictionary of prefilled form fields
    :param conditions: List of conditions to include in the policy
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Dictionary with the following keys:
        url: URL to post to
        fields: Dictionary of form fields and values to submit with the POST
    :return: None if error.
    """

    # Generate a presigned S3 POST URL
    try:
        response = await asyncio.to_thread(
          client.generate_presigned_url,
          ClientMethod='put_object',
          Params={
            'Bucket': bucket_name,
            'Key': key,
            "ACL": "public-read",
            "ContentType": "image/png",
          },
          ExpiresIn=expiration,
          HttpMethod='Put'
        )
    except ClientError as e:
        return None
    else:
      # format response to post url
      print('trying url')
      # The response contains the layer title and the presigned URL
      return (title,response)