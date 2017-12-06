import asyncio
import gbulb
from pandora import Client
from secrety import SecretService

gbulb.install()
loop = asyncio.get_event_loop()
client = Client()


async def login():
    ss = SecretService()
    await ss.unlock_keyring()
    email = 'tngpng@gmail.com'
    password = await ss.get_account_password(email)
    print(password)
    response = await client.login(email, password)
    print(response)
    stations = await client.get_stations()
    print(stations)
    playlist = await client.get_playlist_fragment(stations[0])
    print(playlist)

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
