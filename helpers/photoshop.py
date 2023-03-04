import asyncio
from typing import Tuple
import aiohttp
import aiofiles
import requests
from flask import abort
import jwt
import time
import os

API_KEY = os.environ.get('PHOTOSHOP_CLIENT_ID')
CLIENT_SECRET = os.environ.get('PHOTOSHOP_CLIENT_SECRET')
ORG_ID = os.environ.get('PHOTOSHOP_ORG_ID')
TECH_ID = os.environ.get('PHOTOSHOP_TECHNICAL_ACCOUNT_ID')

def poll_api(
  access_token:str,
  url:str,
  timeout:int = 60,
  poll_interval:int = 4
):
    headers = {
        "Content-Type": 'application/json',
        "Authorization": f"Bearer {access_token}",
        "x-api-key": API_KEY
    }
    start_time = time.time()
    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        diff_time = time.time() - start_time
        print('------------')
        print(response)
        print(diff_time)
        print(data)
        status = (data.get('outputs', [{}])[0].get('status', 'failed'))
        if response.status_code >= 400 or status == 'failed':
            abort(data.get('code', 400), data.get('details', [{}])[0].get('reason', "Photoshop polling failed"))
        elif diff_time > timeout:
            # Timeout reached.
            abort(408, "Timeout reached for photoshop api")
        else:
            if status in ['running', 'pending']:
              time.sleep(poll_interval)
            else:
              print('completed')
              return data

async def psd_edit(session: aiohttp.ClientSession, access_token: str, payload: dict) -> dict:
    """
    Edit a psd using the PhotoshopApi
      :param session: aiohttp.ClientSession
      :param access_token: str
      :param payload: dict
      :return: access_token as a string.
    """
    headers = {
        "Content-Type": 'application/json',
        "Authorization": f"Bearer {access_token}",
        "x-api-key": API_KEY
    }

    response = await session.post(
        'https://image.adobe.io/pie/psdService/text',
        json=payload,
        headers=headers
    )
    data = await response.json()
    print(data, response.status)
    if response.status >= 400:
      print('Error occurred for photoshop api')
      abort(data.get('code', 400), data.get('title', "Unknown photoshop api error"))

    url = data.get('_links', {}).get('self', {}).get('href')
    if not url:
      abort(400, "Photoshop polling url is invalid")
    result = poll_api(access_token, url, timeout=120)
    return

async def get_access_token(session: aiohttp.ClientSession) -> str:
  """
  Get access token from Photoshop Api 
    :param session: aiohttp.ClientSession
    :return: access_token as a string.
  """
  ims = "https://ims-na1.adobelogin.com"
  filename = os.path.join('secrets', 'ps_private.key')
  print('retreiving private key', filename)
  async with aiofiles.open(filename, mode='r') as f:
    private_key_unencrypted = await f.read()
  header_jwt = {'cache-control':'no-cache','content-type':'application/x-www-form-urlencoded'}
  jwt_payload = {
      "exp": round(24*60*60+ int(time.time())),###Expiration set to 24 hours
      "iss": ORG_ID,
      "sub": TECH_ID,
      f"{ims}/s/ent_ccas_sdk": True,
      "aud": f"{ims}/c/{API_KEY}"
  }
  encoded_jwt = jwt.encode(jwt_payload, private_key_unencrypted , algorithm='RS256')
  payload = {
    "client_id": API_KEY,
    "client_secret": CLIENT_SECRET,
    "jwt_token" : encoded_jwt
  }

  response = await session.post(f"{ims}/ims/exchange/jwt/", data=payload)
  data = await response.json()
  access_token = data['access_token']
  expire = data['expires_in']
  print(f"Expires: {expire}")
  return access_token
