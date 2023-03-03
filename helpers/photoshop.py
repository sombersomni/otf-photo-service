import asyncio
import aiohttp
  
async def poll_request(url:str, timeout:int = 60, poll_interval:int = 2):
  loop = asyncio.get_event_loop()
  async with aiohttp.ClientSession() as session:
    start_time = loop.time()
    while True:
        response = await session.get(url)
        diff_time = loop.time() - start_time
        print(diff_time)
        if response.status == 200:
            # Success! Do something with the response here.
            data = await response.json()
            return response
        elif diff_time > timeout:
            # Timeout reached.
            return None
        else:
            # Endpoint not yet available. Wait and try again.
            await asyncio.sleep(poll_interval)