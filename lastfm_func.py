import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

lastfm_api_key = os.getenv('LASTFM_API_KEY')


async def get_list_similar_tracks(tracks):
    similar_tracks = []
    async with aiohttp.ClientSession() as session:
        for track in tracks:
            track_name = track[1]
            artist_name = track[2]
            similar = await get_similar_track(track_name, artist_name, session)
            similar_tracks += similar

    return similar_tracks


async def get_similar_track(track_name, artist_name, session):
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "track.getsimilar",
        "api_key": lastfm_api_key,
        "format": "json",
        "limit": 5,
        "track": track_name,
        "artist": artist_name
    }
    async with session.get(url, params=params) as resp:
        resp.raise_for_status()
        data = await resp.json()
        result = [track["name"] for track in data["similartracks"]["track"]]
        return result
