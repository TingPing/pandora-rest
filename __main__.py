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
    # genre_categories =  await client.get_genre_categories()
    # print(genre_categories)
    # genres_stations = await client.get_genre_category_stations(genre_categories[0])
    # print(genres_stations)
    # recommendations = await client.get_station_recommendations()
    # print(recommendations)
    # filter_enabled = await client.get_explicit_content_filter()
    # print(filter_enabled)
    # await client.set_explicit_content_filter(not filter_enabled, email, password)  
    stations = await client.get_stations()
    print(stations)
    station = stations[0]
    print(station)
    # await client.update_station(station, name='Super Awesome Jams')
    # await client.update_station(station, description='Nothing but the most Super Awesome Jams')
    playlist = await client.get_playlist_fragment(station)
    print(playlist)
    track = playlist[0]
    print(track)
    # track_with_lyrics = None
    # for track in playlist:
        # if track.lyric_id:
            # track_with_lyrics = track
            # break
    # lyric = await client.get_lyrics(track_with_lyrics)
    # print(track_with_lyrics)
    # for line in lyric.lines:
        # print(line)
    # artist_info = await client.get_artist_info(track.artist_seo_token)
    # print(artist_info.bio)
    # search = await client.search('Pantera')
    # print(search)
    with open('output.mp3', 'wb') as f:
        session = soupy.Session()
        response = await session.get(track.audio_url)
        f.write(response.body)

    station_art_url = station.art.get_url_for_size(500)

    if station_art_url:
        with open('station-art.jpeg', 'wb') as f:
            session = soupy.Session()
            response = await session.get(station_art_url)
            f.write(response.body)

    cover_art_url = track.art.get_url_for_size(500)

    if cover_art_url:
        with open('cover-art.jpeg', 'wb') as f:
            session = soupy.Session()
            response = await session.get(cover_art_url)
            f.write(response.body)

asyncio.ensure_future(login()).add_done_callback(lambda x: loop.stop())

loop.run_forever()
