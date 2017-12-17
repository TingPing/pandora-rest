import enum
import soupy
from typing import List
from bisect import bisect_left


class AudioFormat(enum.Enum):
    """Supported formats to request"""
    MP3 = 'mp3'
    MP3_HIFI = 'mp3-hifi'
    AACPLUS = 'aacplus'


class NewStationType(enum.Enum):
    SONG = 0
    ARTIST = 1


class TrackRating(enum.IntEnum):
    """Pandora Track Ratings"""
    NONE = 0
    LOVED = 1
    BANNED = 2


class SearchType(enum.Enum):
    """Supported search types"""
    ALL = 'all'
    TRACK = 'track'
    ARTIST = 'artist'

class ResultType(enum.Enum):
    """Search result types"""
    TRACK = 'track'
    ARTIST = 'artist'


class Art:
    def __init__(self, art: dict) -> None:
        self._art = art
        self.x_small = self._art.get('90')
        self.small = self._art.get('130')
        self.medium = self._art.get('500')
        self.large = self._art.get('640')
        self.x_large = self._art.get('1080')
        self._sizes = []
        for k in self._art.keys():
            try:
                self._sizes.append(int(k))
            except ValueError:
                continue
        self._sizes.sort()

    def get_best_url_for_size(self, size: int) -> str:
        """
        Obtains the Url of the art that is closest in size
        to the desired size or an empty string if there is no art.
        If two sizes are equally close to the desired size,
        return the larger of the two size's Url.

        :param size: desired size in px
        :returns: art Url or empty string
        """
        if not self._art:
            return ''
        elif not self._sizes:
            return list(self._art.values())[0]
        elif size in self._sizes:
            closest = size
        else:
            pos = bisect_left(self._sizes, size)
            if pos == len(self._sizes):
                closest = self._sizes[-1]
            else:
                closest = self._sizes[pos]
        return self._art.get(str(closest), '')

class Track:
    def __init__(self, data: dict) -> None:
        # Must have
        self.title = data['songTitle']
        self.album_title = data['albumTitle']
        self.artist_name = data['artistName']
        self.music_id = data['musicId']
        self.artist_music_id = data['artistMusicId']
        self.pandora_id = data['pandoraId']
        self.token = data['trackToken']
        self.station_id = data['stationId']
        self.audio_url = data['audioURL']
        # Nice to have
        self.rating = TrackRating(int(data.get('rating', 0)))
        self.length = int(data.get('trackLength', 0))
        self.gain = float(data.get('fileGain', 0.0))
        self.audio_encoding = data.get('audioEncoding', '')
        self.art = Art({i['size']: i['url'] for i in data.get('albumArt', [])})
        self.artist_art = Art({i['size']: i['url'] for i in data.get('artistArt', [])})
        self.genre = data.get('genre', [])
        self.user_seed = data.get('userSeed')
        self.is_seed = data.get('isSeed', False)
        self.is_bookmarked = data.get('isBookmarked', False)

    def __repr__(self):
        return "<Track '{}: {}'>".format(self.artist_name, self.title)


class StationSeed:
    def __init__(self, seed: dict) -> None:
        self.music_id = seed.get('musicId')
        self.pandora_id = seed.get('pandoraId')


class Station:
    def __init__(self, data: dict) -> None:
        # Must have
        self.name = data['name']
        self.station_id = data['stationId']
        self.pandora_id = data['pandoraId']
        # Nice to have
        self.initial_seed = StationSeed(data.get('initialSeed', {}))
        self.allow_add_seed = data.get('allowAddSeed', False)
        self.art = Art({i['size']: i['url'] for i in data.get('art', [])})
        self.is_thumbprint = data.get('isThumbprint', False)
        self.is_shuffle = data.get('isShuffle', False)
        self.genre = data.get('genre', [])

    def __repr__(self):
        return "<Station '{}: {}'>".format(self.name, self.station_id)

class SearchResult:
    def __init__(self, result: dict) -> None:
        self.result_type = ResultType(result['type'])
        if self.result_type is ResultType.ARTIST:
            self.artist_name = result['name']
            self.track_name = ''
        elif self.result_type is ResultType.TRACK:
            self.artist_name = result['artistName']
            self.track_name = result['name']
        self.music_id = result['musicId']
        self.art = Art({i['size']: i['url'] for i in result.get('art', [])})

    def __repr__(self):
        return "<SearchResult '{}: {}'>".format(self.result_type.name, self.music_id)


class Client:
    def __init__(self):
        self._session = soupy.Session()
        self._hifi_available = False
        self._auth_token = ''
        self._csrf_token = ''

    async def _get_csrf_token(self) -> str:
        await self._session.head('https://www.pandora.com')
        return self._session.cookies['csrftoken']

    async def _send_message(self, method: str, body: dict) -> dict:
        uri = 'https://www.pandora.com/api/' + method
        headers = {'X-CsrfToken': self._csrf_token, 'X-AuthToken': self._auth_token}
        response = await self._session.post(uri, json_body=body, headers=headers)
        return response.json_body

    async def login(self, email: str, password: str) -> None:
        """
        Obtains a users auth-token and stores it in the session.
        Required before any other calls.

        :param email: Users email
        :param password: Users password
        """
        self._csrf_token = await self._get_csrf_token()
        response = await self._send_message('v1/auth/login', {
            'username': email,
            'password': password,
        })

        flags = response.get('config', {}).get('flags', [])
        self._hifi_available = 'highQualityStreamingAvailable' in flags
        self._auth_token = response['authToken']

    async def get_stations(self, amount: int=250) -> List[Station]:
        """
        Obtains users stations.

        :param amount: Max number to retreive.
        """
        response = await self._send_message('v1/station/getStations', {
            'pageSize': amount,
        })
        return [Station(s) for s in response['stations']]

    async def create_new_station_based_on_track(self, track: Track,
                                                new_station_type: NewStationType) -> Station:
        """
        Creates a new station based on a track.

        :param track: the track the new station is based on.
        :param new_station_type: the NewStationType.
        """
        if new_station_type is NewStationType.SONG:
            music_id = track.music_id
        else:
            music_id = track.artist_music_id
        station_code = 'mc' + music_id
        response = await self._send_message('v1/station/createStation', {
            'stationCode': station_code,
        })
        return Station(response)

    async def get_playlist_fragment(self, station: Station, is_start: bool=True,
                                    audio_format: AudioFormat=AudioFormat.MP3) -> List[Track]:
        """
        Gets a playlist (list of tracks) for a station.

        :param station: Station to get tracks for.
        :param is_start: If this is the first playlist.
        :param audio_format: Format for urls in tracks
        """
        response = await self._send_message('v1/playlist/getFragment', {
            'stationId': station.station_id,
            'isStationStart': is_start,
            'fragmentRequestReason': 'Normal',  # TODO
            'audioFormat': audio_format.value,  # TODO: aacplus and maybe more formats
        })
        return [Track(t) for t in response['tracks']]

    async def tired_track(self, track: Track) -> None:
        """
        Set a track Tired.

        :param track: The track to be set Tired.
        """
        await self._send_message('v1/listener/addTiredSong', {
            'trackToken': track.token,
        })

    async def add_bookmark(self, music_id: str) -> None:
        """
        Bookmark a track or artist.

        :music_id: musicId or artistMusicId.
        """
        await self._send_message('v1/bookmark/add', {
            'musicId': music_id,
        })

    async def delete_bookmark(self, music_id: str) -> None:
        """
        Delete a previously bookmarked track or artist.

        :music_id: musicId or artistMusicId.
        """
        await self._send_message('/v1/bookmark/delete', {
            'musicId': music_id,
        })

    async def rate_track(self, track: Track, track_rating: TrackRating) -> None:
        """
        Rate a track.

        :param track: The track to be rated.
        :param track_rating: The new TrackRating.
        """
        if track_rating is TrackRating.NONE:
            if track.rating is not TrackRating.NONE:
                await self._send_message('v1/station/deleteFeedback', {
                    'trackToken': track.token,
                    'isPositive': True,
                })

        elif track_rating is not track.rating:
            is_positive = track_rating is TrackRating.LOVED
            await self._send_message('v1/station/addFeedback', {
                'trackToken': track.token,
                'isPositive': is_positive,
            })

    async def get_replay_track(self, track: Track, last_played_track_token: str) -> Track:
        """
        Gets a fresh track for replay.

        :param track: The track to be replayed.
        :param last_played_track_token: The trackToken of the last played track.
        """
        response = await self._send_message('v1/ondemand/getReplayTrack', {
            'stationId': track.station_id,
            'trackToken': track.token,
            'lastPlayedTrackToken': last_played_track_token,
        })
        return Track(response['replayTrack'])

    async def search(self, query: str, search_type: SearchType=SearchType.ALL,
                     max_items_per_category: int=50) -> List[SearchResult]:
        """
        Obtains search results.

        :param query: A query string.
        :param search_type: SearchType.
        :param max_items_per_category: Max Items Per Category.
        """
        # TODO: search genre stations
        response = await self._send_message('v1/search/fullSearch', {
            'query': query,
            'type': search_type.value,
            'maxItemsPerCategory': max_items_per_category,
        })
        return [SearchResult(r) for r in response['items']]
