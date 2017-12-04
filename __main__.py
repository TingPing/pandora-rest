import asyncio
import gbulb
from pandora import Client

gbulb.install()
loop = asyncio.get_event_loop()
client = Client()


async def login():
    response = await client.login('tngpng@gmail.com', 'password')
    print(response)
    stations = await client.get_stations()
    print(stations)
    playlist = await client.get_playlist_fragment(stations[0])
    print(playlist)
    

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
