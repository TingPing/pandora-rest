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
    # filter_enabled = await client.get_explicit_content_filter()
    # print(filter_enabled)
    # await client.set_explicit_content_filter(not filter_enabled, email, password)  
    stations = await client.get_stations()
    print(stations)
    station = stations[0]
    # await client.update_station(station, name='Super Awesome Jams')
    # await client.update_station(station, description='Nothing but the most Super Awesome Jams')
    playlist = await client.get_playlist_fragment(station)
    print(playlist)
    # artist_info = await client.get_artist_info(playlist[0].artist_music_id)
    # print(artist_info.bio)
    search = await client.search('Pantera')
    print(search)
    with open('output.mp3', 'wb') as f:
        session = soupy.Session()
        response = await session.get(playlist[0].audio_url)
        f.write(response.body)

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
