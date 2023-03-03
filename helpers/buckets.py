import asyncio
from io import BytesIO
from typing import Iterable
from PIL import Image

from constants import Key_Title_Zip, Title_Image_Zip

async def get_image(client,  bucket_name: str, key_title_zip: Key_Title_Zip):
    key, title = key_title_zip
    if key.endswith('.jpg') or key.endswith('.jpeg') or key.endswith('.png'):
        response = await asyncio.to_thread(client.get_object, Bucket=bucket_name, Key=key)
        img_bytes = BytesIO(response['Body'].read())
        img = Image.open(img_bytes)
        return Title_Image_Zip(title, img)

async def get_images_from_s3_keys(client, bucket_name: str, key_title_zipped: Iterable[Key_Title_Zip]):
    return await asyncio.gather(
      *[get_image(client, bucket_name, key_title_zip) for key_title_zip in key_title_zipped],
      return_exceptions=True
    )
