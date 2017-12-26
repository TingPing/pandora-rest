import enum
import soupy
from typing import List, Optional
from bisect import bisect_left


class AudioFormat(enum.Enum):
    """Supported formats to request"""
    MP3 = 'mp3'
    MP3_HIFI = 'mp3-hifi'
    AACPLUS = 'aacplus'


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
    GENRE = 'genre'


class RecommendationType(enum.Enum):
    """Station recommendation types"""
    GENRE = 'genreStations'
    ARTIST = 'artists'


class StationSeedType(enum.Enum):
    """Station seed types"""
    TRACK = 0
    ARTIST = 1
    GENRE = 2


class Art:
    """Art in various sizes from 90 to 1080px"""
    def __init__(self, art: dict) -> None:
        self._art = art
        self._sizes = sorted(self._art.keys())

    def get_url_for_size(self, size: int) -> str:
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
        elif size in self._sizes:
            closest = size
        else:
            pos = bisect_left(self._sizes, size)
            if pos == len(self._sizes):
                closest = self._sizes[-1]
            else:
                closest = self._sizes[pos]
        return self._art[closest]

    def __repr__(self):
        return "<Art '{}'>".format(self.get_url_for_size(90))


class TrackBase:
    """Base class for all Track like objects"""
    def __init__(self, data: dict) -> None:
        self.music_id = data['musicId']
        self.title = data['songTitle']
        self.album_title = data['albumTitle']
        self.artist_name = data['artistName']
        self.album_seo_token = data['albumSeoToken']
        self.artist_seo_token = data['artistSeoToken']
        self.track_seo_token = data['trackSeoToken']
        self.pandora_id = data['pandoraId']
        self.amazon_url = data['amazonUrl']
        self.length = int(data.get('trackLength', 0))
        self.art = Art({i['size']: i['url'] for i in data.get('albumArt', [])})


class ArtistBase:
    """Base class for all Artist like objects"""
    def __init__(self, data: dict) -> None:
        self.artist_name = data['name']
        self.artist_music_id = data['musicId']
        self.artist_seo_token = data['seoToken']
        self.pandora_id = data['pandoraId']
        self.art = Art({i['size']: i['url'] for i in data.get('art', [])})


class AlbumBase:
    """Base class for all Album like objects"""
    def __init__(self, data: dict) -> None:
        self.album_seo_token = data['seoToken']
        self.album_title = data['albumTitle']
        self.pandora_id = data['pandoraId']
        self.art = Art({i['size']: i['url'] for i in data.get('art', [])})


class StationBase:
    """Base class for most Station like objects"""
    def __init__(self, data: dict) -> None:
        self.name = data['name']
        self.station_id = data['stationId']
        self.pandora_id = data['pandoraId']
        self.is_shared = data['isShared']
        self.is_transform_allowed = data['isTransformAllowed']
        self.is_thumbprint = data['isThumbprint']
        self.is_shuffle = data['isShuffle']
        self.allow_add_seed = data['allowAddSeed']
        self.genre = data['genre']
        self.allow_delete = data['allowDelete']
        self.allow_edit_description = data['allowEditDescription']
        self.allow_rename = data['allowRename']
        self.description = data.get('description', '')
        self.art = Art({i['size']: i['url'] for i in data.get('art', [])})


class Track(TrackBase):
    """
    A playlist Track as returned from client.get_playlist_fragment or client.get_replay_track

    Endpoint(s): v1/playlist/getFragment, v1/ondemand/getReplayTrack

    Base class: TrackBase
    """
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.artist_music_id = data['artistMusicId']
        self.token = data['trackToken']
        self.station_id = data['stationId']
        self.audio_url = data['audioURL']
        self.rating = TrackRating(int(data['rating']))
        self.gain = float(data.get('fileGain', 0.0))
        self.audio_encoding = data['audioEncoding']
        self.artist_art = Art({i['size']: i['url'] for i in data.get('artistArt', [])})
        self.genre = data['genre']
        self.is_seed = data['isSeed']
        self.is_bookmarked = data['isBookmarked']
        self.lyric_id = data.get('lyricSnippet', {}).get('lyricId', '')
        self.lyric_checksum = data.get('lyricSnippet', {}).get('checksum', 0)

    def __repr__(self):
        return "<Track '{}: {}'>".format(self.artist_name, self.title)


class Lyric:
    """
    Track Lyrics as returned from client.get_lyrics

    Endpoint(s): v1/music/fullLyrics
    """
    def __init__(self, data: dict) -> None:
        self.lyric_id = data['lyricId']
        self.lyric_checksum = data['checksum']
        self.lines = data['lines']
        self.credits = data.get('credits', [])

    def __repr__(self):
        return "<Lyric '{}: {}'>".format(self.lyric_id, self.lyric_checksum)


class ArtistInfo(ArtistBase):
    """
    Artist info as returned from client.get_artist_info

    Endpoint(s): v1/music/artist

    Base class: ArtistBase
    """
    def __init__(self, info: dict) -> None:
        super().__init__(info)
        self.bio = info.get('bio', '')
        self.is_bookmarked = info['isBookmarked']
        self.discography = [DiscographyAlbum(a) for a in info.get('discography', [])]
        self.similar = [SimilarArtist(a) for a in info.get('similar', [])]

    def __repr__(self):
        return "<ArtistInfo '{}: {}'>".format(self.artist_name, self.artist_seo_token)


class DiscographyAlbum(AlbumBase):
    """
    Artist info discography album

    Base class: AlbumBase
    """
    def __init__(self, album: dict) -> None:
        super().__init__(album)
        self.year = album.get('year', 0)

    def __repr__(self):
        return "<DiscographyAlbum '{}: {}'>".format(self.album_title, self.album_seo_token)


class SimilarArtist(ArtistBase):
    """
    Artist info similar artist

    Base class: ArtistBase
    """
    def __init__(self, similar: dict) -> None:
        super().__init__(similar)

    def __repr__(self):
        return "<SimilarArtist '{}: {}'>".format(self.artist_name, self.artist_music_id)


class AlbumInfo(AlbumBase):
    """
    Album info as returned from client.get_album_info

    Endpoint(s): v1/music/album

    Base class: AlbumBase
    """
    def __init__(self, info: dict) -> None:
        super().__init__(info)
        self.review = info.get('review', '')
        self.album_seo_token = info['seoToken']
        self.artist_seo_token = info['artistSeoToken']
        self.artist_name = info['artistName']
        self.pandora_id = info['pandoraId']
        self.is_bookmarked = info['isBookmarked']
        self.amazon_url = info['amazonUrl']
        self.tracks = [InfoTrack(t) for t in info.get('tracks', [])]

    def __repr__(self):
        return "<AlbumInfo '{}: {}'>".format(self.album_title, self.artist_name)


class TrackInfo(TrackBase):
    """
    Track info as returned from client.get_track_info

    Endpoint(s): v1/music/track

    Base class: TrackBase
    """
    def __init__(self, info: dict) -> None:
        super().__init__(info)
        self.focus_traits = info.get('focusTraits', [])
        self.lyric_id = info.get('lyricSnippet', {}).get('lyricId', '')
        self.lyric_checksum = info.get('lyricSnippet', {}).get('checksum', 0)
        self.is_bookmarked = info['isBookmarked']
        self.similar = [InfoTrack(a) for a in info.get('similar', [])]

    def __repr__(self):
        return "<TrackInfo '{}: {}'>".format(self.title, self.track_seo_token)


class InfoTrack(TrackBase):
    """
    Info Track

    Base class: TrackBase
    """
    def __init__(self, track: dict) -> None:
        super().__init__(track)

    def __repr__(self):
        return "<InfoTrack '{}: {}'>".format(self.title, self.track_seo_token)


class Station(StationBase):
    """
    Station as returned from client.get_stations

    Endpoint(s): v1/station/getStations

    Base class: StationBase
    """
    def __init__(self, data: dict) -> None:
        super().__init__(data)

    def __repr__(self):
        return "<Station '{}: {}'>".format(self.name, self.station_id)

class StationInfo(StationBase):
    """
    Station info as returned from client.get_station_info

    Endpoint(s): v1/station/getStationDetails

    Base class: StationBase
    """
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.seeds = [StationSeed(s) for s in data.get('seeds', [])]

    def __repr__(self):
        return "<StationInfo '{}: {}'>".format(self.name, self.station_id)


class StationSeed:
    """Station info station seed"""
    def __init__(self, seed: dict) -> None:
        if 'artist' in seed:
            self.seed_type = StationSeedType.ARTIST
            artist = seed['artist']
            self.artist_music_id = seed.get('musicId', '')
            self.music_id = ''
            self.genre_music_id = ''
            self.track_name = ''
            self.artist_name = artist.get('artistName', '')
            self.album_title = ''
            self.station_name = ''
            self.art = Art({i['size']: i['url'] for i in artist.get('art', [])})
        elif 'song' in seed:
            self.seed_type = StationSeedType.TRACK
            track = seed['song']
            self.artist_music_id = ''
            self.music_id = seed.get('musicId', '')
            self.genre_music_id = ''
            self.track_name = track.get('songTitle', '')
            self.artist_name = track.get('artistSummary', '')
            self.album_title = track.get('albumTitle', '')
            self.station_name = ''
            self.art = Art({i['size']: i['url'] for i in track.get('art', [])})
        elif 'genre' in seed:
            self.seed_type = StationSeedType.GENRE
            genre = seed['genre']
            self.artist_music_id = ''
            self.music_id = ''
            self.genre_music_id = seed.get('musicId', '')
            self.track_name = ''
            self.artist_name = ''
            self.album_title = ''
            self.station_name = genre.get('stationName', '')
            self.art = Art({i['size']: i['url'] for i in genre.get('art', [])})
        self.pandora_id = seed.get('pandoraId')

    def __repr__(self):
        music_id = self.artist_music_id or self.music_id or self.genre_music_id
        return "<StationSeed '{}: {}'>".format(self.seed_type.name, music_id)


class StationSeedSuggestion:
    """
    Station seed suggestion as returned from client.get_station_seed_suggestions

    Endpoint(s): v1/search/getSeedSuggestions
    """
    def __init__(self, seed: dict) -> None:
        self.artist_name = seed.get('name', '')
        self.artist_music_id = seed.get('musicId', '')
        self.art = Art({i['size']: i['url'] for i in seed.get('art', [])})

    def __repr__(self):
        return "<StationSeedSuggestion '{}: {}'>".format(self.artist_name, self.artist_music_id)


class SearchResult:
    """
    Search result as returned from client.search

    Endpoint(s): v1/search/fullSearch
    """
    def __init__(self, result: dict, query: str) -> None:
        self.query = query
        self.result_type = ResultType(result['type'])
        if self.result_type is ResultType.ARTIST:
            self.artist_name = result['name']
            self.track_name = ''
            self.station_name = ''
            self.music_id = ''
            self.artist_music_id = result['musicId']
        elif self.result_type is ResultType.TRACK:
            self.artist_name = result['artistName']
            self.track_name = result['name']
            self.station_name = ''
            self.music_id = result['musicId']
            self.artist_music_id = ''
        elif self.result_type is ResultType.GENRE:
            self.artist_name = ''
            self.track_name = ''
            self.station_name = result['name']
            self.music_id = ''
            self.artist_music_id = ''
            self.genre_music_id = result['musicId']
        self.art = Art({i['size']: i['url'] for i in result.get('art', [])})

    def __repr__(self):
        return "<SearchResult '{}: {}'>".format(self.result_type.name, self.music_id)


class StationRecommendation:
    """
    Search result as returned from client.get_station_recommendations

    Endpoint(s): v1/search/getStationRecommendations
    """
    def __init__(self, rec: dict, rec_type: RecommendationType) -> None:
        self.recommendation_type = rec_type
        if self.recommendation_type is RecommendationType.ARTIST:
            self.artist_name = rec['name']
            self.artist_music_id = rec['musicId']
            self.station_name = ''
            self.genre_music_id = ''
            self.description = ''
            self.sample_tracks = []
            self.art = Art({i['size']: i['url'] for i in rec.get('art', [])})
        elif self.recommendation_type is RecommendationType.GENRE:
            self.artist_name = ''
            self.artist_music_id = ''
            self.station_name = rec['name']
            self.genre_music_id = rec['musicId']
            self.description = rec.get('description', '')
            self.sample_tracks = [InfoTrack(t) for t in rec.get('sampleTracks', [])]
            self.art = Art({i['size']: i['url'] for i in rec.get('headerArt', [])})

    def __repr__(self):
        music_id = self.artist_music_id or self.genre_music_id
        return "<StationRecommendation '{}: {}'>".format(self.recommendation_type.name, music_id)


class GenreCategory:
    """
    Genre category as returned from client.get_genre_categories

    Endpoint(s): v1/music/genrecategories
    """
    def __init__(self, category: dict) -> None:
        self.name = category.get('name', '')
        self.token = category.get('token', '')
        self.art = Art({i['size']: i['url'] for i in category.get('art', [])})

    def __repr__(self):
        return "<GenreCategory '{}: {}'>".format(self.name, self.token)


class GenreStation:
    """
    Genre station as returned from client.get_genre_category_stations

    Endpoint(s): v1/music/genres
    """
    def __init__(self, station: dict) -> None:
        self.name = station.get('name', '')
        self.genre_music_id = station.get('musicId', '')
        self.description = station.get('description', '')
        self.art = Art({i['size']: i['url'] for i in station.get('art', [])})
        self.sample_tracks = [InfoTrack(t) for t in station.get('sampleTracks', [])]

    def __repr__(self):
        return "<GenreStation '{}: {}'>".format(self.name, self.genre_music_id)


class Feedback(TrackBase):
    """
    Feedback as returned from client.get_station_feedback

    Endpoint(s): v1/station/getStationFeedback
    """
    def __init__(self, feedback: dict) -> None:
        super().__init__(feedback)
        self.feedback_id = feedback['feedbackId']
        self.is_positive = feedback['isPositive']

    def __repr__(self):
        return "<Feedback '{}: {}'>".format(self.title, self.feedback_id)


class Client:
    """
    Wrapper for the `Pandora REST API <https://6xq.net/pandora-apidoc/rest/>`_.

    Note that :meth:`login()` must be called before any other method.

    All methods raise :class:`SoupException` on failure.
    """
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

        Endpoint(s): v1/auth/login

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

    async def logout(self) -> None:
        """
        Logout of the Pandora session.

        Endpoint(s): v1/auth/logout
        """
        await self._send_message('v1/auth/logout', {})

    async def get_stations(self, amount: int=250) -> List[Station]:
        """
        Obtains users stations.

        Endpoint(s): v1/station/getStations

        :param amount: Max number to retreive.
        :return: A list of Station objects.
        """

        response = await self._send_message('v1/station/getStations', {
            'pageSize': amount,
        })
        return [Station(s) for s in response['stations']]

    async def transform_shared_station(self, station: Station) -> None:
        """
        Transform a shared station to a user station.

        Endpoint(s): v1/station/transformShared

        :param station: The station to be transformed from a shared station to a user station.
        """
        await self._send_message('v1/station/transformShared', {
            'stationId': station.station_id,
        })

    async def create_station(self, music_id: str, name: Optional[str] = None,
                             search_query: Optional[str] = None) -> Station:
        """
        Creates a new station.

        Endpoint(s): v1/station/createStation

        :param music_id: A track_music_id, artist_music_id or genre_music_id.
        :param name: The name of the new station (Optional, 64 char limit).
        :param search_query: The search query if music_id was got from a search (Optional).
        :return: A newly created Station object. If a Station already exists with music_id \
        as one of it's seeds, the Station object will effectively be a copy of that existing Station. 
        """
        sig = 'mc' if music_id.startswith('S') else 'mi'
        station_code = sig + music_id

        response = await self._send_message('v1/station/createStation', {
            'stationCode': station_code,
            'stationName': self._ellipsize(name, 64) if name else '',
            'searchQuery': search_query or '',
        })
        return Station(response)

    async def delete_station(self, station: Station) -> None:
        """
        Deletes a station.

        Endpoint(s): v1/station/removeStation

        :param station: the station to be deleted.
        """
        await self._send_message('v1/station/removeStation', {
            'stationId': station.station_id,
        })

    async def update_station(self, station: Station,
                             name: Optional[str] = None,
                             description: Optional[str] = None) -> None:
        """
        Update a station's name and/or description.

        Endpoint(s): v1/station/updateStation

        :param station: The station to be renamed.
        :param name: The new name of the station (64 char limit) or ``None`` to not change it.
        :param description: The new description of the station (4000 char limit) or ``None`` to not change it.
        """
        await self._send_message('v1/station/updateStation', {
            'stationId': station.station_id,
            'name': self._ellipsize(name, 64) if name else station.name,
            'description': self._ellipsize(description, 4000) if description else station.description,
        })

    async def get_station_info(self, station: Station,
                              is_current_station: Optional[bool] = False) -> StationInfo:
        """
        Get the station's info.

        Endpoint(s): v1/station/getStationDetails

        :param station: The station to be get the info for.
        :is_current_station: If the station is the current station (Optional).
        :return: A StationInfo object.
        """
        response = await self._send_message('v1/station/getStationDetails', {
            'stationId': station.station_id,
            'isCurrentStation': is_current_station,
        })
        return StationInfo(response)

    async def get_station_feedback(self, station: Station, track_rating: TrackRating,
                                   amount: Optional[int] = 10, start_index: Optional[int] = 0) -> List[Feedback]:
        """
        Get a station's feedback.

        Endpoint(s): v1/station/getStationFeedback

        :param station: The station to be get the feedback of.
        :param track_rating: TrackRating.LOVED or TrackRating.BANNED
        :param ammount: The max number of feedbacks to return (Optional).
        :param start_index: The starting index of the feedbacks (Optional).
        :return: List of Feedback objects.
        """

        if track_rating is TrackRating.NONE: # Nothing to do
            return []

        is_positive = track_rating is TrackRating.LOVED

        response = await self._send_message('v1/station/getStationFeedback', {
            'pageSize': amount,
            'startIndex': start_index,
            'stationId': station.station_id,
            'positive': is_positive, 
        })
        return [Feedback(f) for f in response.get('feedback', [])] 

    async def add_station_seed(self, station: Station, music_id: str) -> None:
        """
        Add a seed to a station.

        Endpoint(s): v1/station/addSeed

        :param station: The station to add the seed to.
        :music_id: A track music_id or artist_music_id.
        """
        await self._send_message('v1/station/addSeed', {
            'stationId': station.station_id,
            'musicId': music_id,
        })

    async def delete_station_seed(self, station: Station, music_id: str) -> None:
        """
        Delete a seed from a station.

        Endpoint(s): v1/station/deleteSeed

        :param station: The station to delete the seed from.
        :music_id: A track music_id or artist_music_id.
        """
        await self._send_message('v1/station/deleteSeed', {
            'stationId': station.station_id,
            'musicId': music_id,
        })

    async def get_station_seed_suggestions(self, station: Station, music_id: str,
                                           max_results: Optional[int] = 10) -> List[StationSeedSuggestion]:
        """
        Get station seed suggestions.

        Endpoint(s): v1/search/getSeedSuggestions

        :param station: The station to get seed suggestions for.
        :music_id: A track music_id or artist_music_id.
        :max_results: The max seed suggestions to return (Optional).
        :return: A list of StationSeedSuggestion objects.
        """
        response = await self._send_message('v1/search/getSeedSuggestions', {
            'stationId': station.station_id,
            'seedMusicId': music_id,
            'maxResults': max_results,
        })
        return [StationSeedSuggestion(s) for s in response]

    @staticmethod
    def _ellipsize(string: str, max_size: int) -> str:
        if len(string) > max_size:
            string = string[:max_size - 1] + '…'
        return string

    async def get_playlist_fragment(self, station: Station, is_start: Optional[bool] = True,
                                    audio_format: Optional[AudioFormat] = AudioFormat.MP3) -> List[Track]:
        """
        Gets a playlist (list of tracks) for a station.

        Endpoint(s): v1/playlist/getFragment

        :param station: Station to get tracks for.
        :param is_start: If this is the first playlist (Optional).
        :param audio_format: Format for urls in tracks (Optional).
        :return: A list of Track objects.
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

        Endpoint(s): v1/listener/addTiredSong

        :param track: The track to be set Tired.
        """
        await self._send_message('v1/listener/addTiredSong', {
            'trackToken': track.token,
        })

    async def add_bookmark(self, music_id: str) -> None:
        """
        Bookmark a track or artist.

        Endpoint(s): v1/bookmark/add

        :music_id: musicId or artistMusicId.
        """
        await self._send_message('v1/bookmark/add', {
            'musicId': music_id,
        })

    async def delete_bookmark(self, music_id: str) -> None:
        """
        Delete a previously bookmarked track or artist.

        Endpoint(s): v1/bookmark/delete

        :music_id: musicId or artistMusicId.
        """
        await self._send_message('v1/bookmark/delete', {
            'musicId': music_id,
        })

    async def track_started(self, track: Track) -> None:
        """
        Signal that a track has started.

        Endpoint(s): v1/station/trackStarted

        :param track: The track to be started.
        """
        await self._send_message('v1/station/trackStarted', {
            'trackToken': track.token,
        })

    async def playback_paused(self) -> None:
        """
        Signal that playback has paused.

        Endpoint(s): v1/station/playbackPaused
        """
        await self._send_message('v1/station/playbackPaused', {})

    async def playback_resumed(self, force_active: Optional[bool] = False) -> None:
        """
        Signal that playback has resumed.

        Endpoint(s): v1/station/playbackResumed

        :param force_active: if this session is forced as the active session (Optional).
        """
        await self._send_message('v1/station/playbackResumed', {
            'forceActive': force_active,
        })

    async def get_explicit_content_filter(self) -> bool:
        """
        Get if the explicit content filter is enabled.

        Endpoint(s): v1/listener/updateSettings

        :return: The state of the Explicit Content Filter. True if enabled, False if not.
        """
        response = await self._send_message('v1/listener/updateSettings', {})
        return response['explicitContentFilterEnabled']

    async def set_explicit_content_filter(self, enable: bool, email: str, password: str) -> None:
        """
        Enable or disable the explicit content filter.

        Endpoint(s): v1/listener/updateAccount

        :enable: if the filter should be enabled.
        :param email: Users email
        :param password: Users password
        """
        await self._send_message('v1/listener/updateAccount', {
            'currentUsername': email,
            'currentPassword': password,
            'enableExplicitContentFilter': enable,
        })

    async def rate_track(self, track: Track, track_rating: TrackRating) -> None:
        """
        Rate a track.

        Endpoint(s): v1/station/deleteFeedback, v1/station/addFeedback

        :param track: The track to be rated.
        :param track_rating: The new TrackRating.
        """
        is_positive = track_rating is TrackRating.LOVED

        if track_rating is TrackRating.NONE:
            if track.rating is not TrackRating.NONE:
                await self._send_message('v1/station/deleteFeedback', {
                    'trackToken': track.token,
                    'isPositive': is_positive,
                })

        elif track_rating is not track.rating:
            await self._send_message('v1/station/addFeedback', {
                'trackToken': track.token,
                'isPositive': is_positive,
            })

    async def delete_feedback(self, feedback: Feedback) -> None:
        """
        Delete station feedback.

        Endpoint(s): v1/station/deleteFeedback

        :param feedback: The station feedback to delete.
        """
        await self._send_message('v1/station/deleteFeedback', {
            'feedbackId': feedback.feedback_id,
            'isPositive': feedback.is_positive,
        })

    async def get_replay_track(self, track: Track, last_played_track_token: str) -> Track:
        """
        Gets a fresh track for replay.

        Endpoint(s): 'v1/ondemand/getReplayTrack'

        :param track: The track to be replayed.
        :param last_played_track_token: The trackToken of the last played track.
        :return: A Track object.
        """
        response = await self._send_message('v1/ondemand/getReplayTrack', {
            'stationId': track.station_id,
            'trackToken': track.token,
            'lastPlayedTrackToken': last_played_track_token,
        })
        return Track(response['replayTrack'])

    async def get_artist_info(self, artist_seo_token: str) -> ArtistInfo:
        """
        Get artist info.

        Endpoint(s): v1/music/artist

        :param artist_seo_token: artistSeoToken.
        :return: An ArtistInfo object.
        """
        response = await self._send_message('v1/music/artist', {
            'token': artist_seo_token,
        })
        return ArtistInfo(response)

    async def get_album_info(self, album_seo_token: str) -> AlbumInfo:
        """
        Get album info.

        Endpoint(s): v1/music/album

        :param album_seo_token: albumSeoToken.
        :return: An AlbumInfo object.
        """
        response = await self._send_message('v1/music/album', {
            'token': album_seo_token,
        })
        return AlbumInfo(response)

    async def get_track_info(self, track_seo_token: str) -> TrackInfo:
        """
        Get track info.

        Endpoint(s): v1/music/track

        :param track_seo_token: trackSeoToken.
        :return: A TrackInfo object.
        """
        response = await self._send_message('v1/music/track', {
            'token': track_seo_token,
        })
        return TrackInfo(response)

    async def get_lyrics(self, track: Track) -> Lyric:
        """
        Get track lyrics.

        Endpoint(s): v1/music/fullLyrics

        :param track: the track to get the lyrics for.
        :return: A Lyric object. The Lyric object attributes will be empty \
        if there is no track.lyric_id or track.lyric_checksum.
        """
        if not track.lyric_id or not track.lyric_checksum:
            return Lyric({})

        response = await self._send_message('v1/music/fullLyrics', {
            'trackUid': track.music_id,
            'lyricId': track.lyric_id,
            'checksum': track.lyric_checksum,
            'nonExplicit': False, # TODO Tie this to the explicit content filter setting
        })
        return Lyric(response)

    async def get_genre_categories(self) -> List[GenreCategory]:
        """
        Get genre categories.

        Endpoint(s): v1/music/genrecategories

        :return: A list of GenreCategory objects 
        """
        response = await self._send_message('v1/music/genrecategories', {})
        return [GenreCategory(c) for c in response.get('categories', [])]

    async def get_genre_category_stations(self, genre_category: GenreCategory) -> List[GenreStation]:
        """
        Get genre stations for a category.

        Endpoint(s): v1/music/genres

        :param genre_category: The genre category to get the stations for.
        :return: A list of GenreStation objects for the specified category.
        """

        response = await self._send_message('v1/music/genres', {
            'categoryToken': genre_category.token,
        })
        return [GenreStation(s) for s in response.get('genres', [])]

    async def get_station_recommendations(self) -> List[StationRecommendation]:
        """
        Get station recommendations.

        Endpoint(s): v1/search/getStationRecommendations

        :return: A list of StationRecommendation objects.
        """
        response = await self._send_message('v1/search/getStationRecommendations', {})
        return [StationRecommendation(r, RecommendationType(k)) for k, v in response.items() for r in v]

    async def search(self, query: str, search_type: Optional[SearchType] = SearchType.ALL,
                     max_items_per_category: Optional[int] = 50) -> List[SearchResult]:
        """
        Obtains search results.

        Endpoint(s): v1/search/fullSearch

        :param query: A query string.
        :param search_type: SearchType (Optional).
        :param max_items_per_category: Max Items Per Category (Optional).
        :return: A list of SearchResult objects.
        """
        response = await self._send_message('v1/search/fullSearch', {
            'query': query,
            'type': search_type.value,
            'maxItemsPerCategory': max_items_per_category,
        })
        return [SearchResult(r, query) for r in response['items']]
