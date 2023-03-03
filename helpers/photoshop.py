import asyncio
import aiohttp
import aiofiles
import jwt
import time
import os

API_KEY = os.environ.get('PHOTOSHOP_CLIENT_ID')
CLIENT_SECRET = os.environ.get('PHOTOSHOP_CLIENT_SECRET')
ORG_ID = os.environ.get('PHOTOSHOP_ORG_ID')
TECH_ID = os.environ.get('PHOTOSHOP_TECHNICAL_ID')

async def poll_ps_api(
  url:str,
  access_token: str,
  timeout:int = 60,
  poll_interval:int = 2
):
  headers = {
    "Authorization": f"Bearer {access_token}",
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
  }
  loop = asyncio.get_event_loop()
  async with aiohttp.ClientSession(headers=headers) as session:
    start_time = loop.time()
    while True:
        response = await session.get(url)
        diff_time = loop.time() - start_time
        print(diff_time)
        if response.status == 200:
            # Success! Do something with the response here.
            data = await response.json()
            print(data)
            return response
        elif diff_time > timeout:
            # Timeout reached.
            return None
        else:
            # Endpoint not yet available. Wait and try again.
            await asyncio.sleep(poll_interval)

async def get_access_token(instance_path: str):
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
      f"{ims}/s/ent_user_sdk": True,
      "aud": f"{ims}/c/{API_KEY}"
  }
  encoded_jwt = jwt.encode(jwt_payload, private_key_unencrypted , algorithm='RS256')
  print(encoded_jwt)
  payload = {
    "client_id": API_KEY,
    "client_secret": CLIENT_SECRET,
    "jwt_token" : encoded_jwt
  }
  print(payload)
  async with aiohttp.ClientSession(headers=header_jwt) as session:
    response = await session.post(f"{ims}/ims/exchange/jwt/", data=payload)
    json_response = await response.json()
    print(json_response)
    token = json_response['access_token']
    expire = json_response['expires_in']
    print(expire)
    return token