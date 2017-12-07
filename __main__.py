import asyncio
import gbulb
from pandora import Client
from secrety import SecretService
import soupy

gbulb.install()
loop = asyncio.get_event_loop()
client = Client()


async def login():
    ss = SecretService()
    await ss.unlock_keyring()
    email = 'tngpng@gmail.com'
    password = await ss.get_account_password(email)
    if not password:
        print('Failed to get password')
    await client.login(email, password)
    stations = await client.get_stations()
    print(stations)
    playlist = await client.get_playlist_fragment(stations[0])
    print(playlist)
    with open('output.mp3', 'wb') as f:
        session = soupy.Session()
        response = await session.get(playlist[0].audio_url)
        f.write(response.body)

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
