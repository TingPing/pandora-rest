import enum
import soupy
from typing import List


class AudioFormat(enum.Enum):
    MP3 = 'mp3'
    AACPLUS = 'aacplus'


class Track:
    def __init__(self, data: dict) -> None:
        self.title = data['songTitle']
        self.music_id = data['musicId']
        self.token = data['trackToken']
        self.length = data['trackLength']
        self.gain = float(data['fileGain'])
        self.audio_url = data['audioURL']
        self.audio_encoding = data['audioEncoding']
        self.art = {i['size']: i['url'] for i in data['albumArt']}

    def __repr__(self):
        return "<Track '{}'>".format(self.title)


class Station:
    def __init__(self, data: dict) -> None:
        self.name = data['name']
        self.station_id = data['stationId']
        self.art = {i['size']: i['url'] for i in data['art']}
        self.is_thumbprint = data['isThumbprint']

    def __repr__(self):
        return "<Station '{}'>".format(self.name)


class Client:
    def __init__(self):
        self._session = soupy.Session()
        self._auth_token = ''
        self._csrf_token = ''

    async def _get_csrf_token(self) -> str:
        uri = 'https://www.pandora.com'
        message = soupy.Message.new_for_uri(soupy.Method.HEAD, uri)
        response = await self._session.send_message(message)
        self._session.save_cookies_from_response(response, uri)
        return self._session.cookies['csrftoken']

    async def _send_message(self, method: str, body: dict) -> dict:
        uri = 'https://www.pandora.com/api/' + method
        message = soupy.Message.new_for_uri(soupy.Method.POST, uri)
        message.headers = {'X-CsrfToken': self._csrf_token,
                           'X-AuthToken': self._auth_token}
        message.json_body = body

        response = await self._session.send_message(message)
        return response.json_body

    async def login(self, email: str, password: str) -> dict:
        self._csrf_token = await self._get_csrf_token()

        response = await self._send_message('v1/auth/login', {
            'username': email,
            'password': password,
        })
        self._auth_token = response['authToken']
        return response

    async def get_stations(self, amount: int=250) -> List[Station]:
        response = await self._send_message('v1/station/getStations', {
            'pageSize': amount,
        })
        return [Station(s) for s in response['stations']]

    async def get_playlist_fragment(self, station: Station, is_start=True,
                                    audio_format: AudioFormat=AudioFormat.MP3) -> List[Track]:
        response = await self._send_message('v1/playlist/getFragment', {
            'stationId': station.station_id,
            'isStationStart': is_start,
            'fragmentRequestReason': 'Normal',  # TODO
            'audioFormat': audio_format.value,  # TODO: aacplus and maybe more formats
        })
        return [Track(t) for t in response['tracks']]
