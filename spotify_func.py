from dotenv import load_dotenv
import os
import base64
import asyncio
import aiohttp
from helpers import get_auth_header
from db import create_session, get_artist_genres_cached, set_artist_genres_cached, cache_track

load_dotenv()

spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')


async def get_token():
    auth_string = spotify_client_id + ':' + spotify_client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')

    url = "https://accounts.spotify.com/api/token"
    headers = {
        'Authorization': 'Basic ' + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as response:
            json_result = await response.json()
            token = json_result['access_token']
            return token


async def add_tracks_genre(data, token, session_http, session_db):
    local_cache = {}
    for item in data["items"]:
        track = item.get("track")
        if not track or track.get("is_local"):
            continue

        artist_id = track["artists"][0]["id"]

        genres = (local_cache.get(artist_id) if local_cache.get(artist_id) is not None else await get_artist_genres_cached(session_db, artist_id))
        if genres is None:
            genres = await get_genres_by_artist_id(artist_id, token, session_http)
            await set_artist_genres_cached(session_db, artist_id, genres)
        local_cache[artist_id] = genres
        track["genres"] = genres

        await cache_track(session_db, track, genres)


async def get_genres_by_artist_id(id, token, session):
    headers = get_auth_header(token)
    url = f"https://api.spotify.com/v1/artists/{id}"
    params = {"fields": "genres"}

    async with session.get(url, headers=headers, params=params) as resp:
        if resp.status == 404:
            return None
        resp.raise_for_status()
        json_data = await resp.json()
        return json_data["genres"]


async def get_tracks_from_playlist_json(playlist_id, token, market="ES"):
    headers = get_auth_header(token)  # headers для всех запросов

    info_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"  # url
    info_fields = "public,owner(display_name),description,name,id"  # что хочу узнать о плейлисте
    info_params = {
        "market": market,
        "fields": info_fields
    }  # словарь для получения инфы о треках

    async with aiohttp.ClientSession() as session_http:
        # Получение инфы о плейлисте
        async with session_http.get(info_url, headers=headers, params=info_params) as playlist_resp:
            if playlist_resp.status == 404:
                return None

            playlist_resp.raise_for_status()

            playlist_info = await playlist_resp.json()  # конвертация в json
            playlist_info["owner"] = playlist_info["owner"]["display_name"]  # упростим структуру словаря

            if playlist_info["public"] is False:
                return None

        tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # url для треков
        track_fields = "items(track(id,name,artists(id,name),duration_ms,popularity,is_local,album(name))),next"  # что хотим от каждого трека
        track_params = {
            "market": market,
            "fields": track_fields,
            "limit": 100
        }  # параметры для получения треков
        all_tracks = []  # список словарей - треков

        async with create_session() as session_db:
            while tracks_url:
                for attempt in range(3):  # время обращения с повторными попытками
                    async with session_http.get(tracks_url, headers=headers,
                                                params=track_params) as tracks_res:  # сессия обращения для получения страницы
                        if tracks_res.status == 429:  # если превысили время ожидания
                            await asyncio.sleep(
                                int(tracks_res.headers.get("Retry-After", "1")))  # ждём необходимое время ожидания
                            max_retries = 3
                            if attempt < max_retries - 1:
                                continue  # следующая попытка

                        tracks_res.raise_for_status()  # проверка на ошибку после всех попыток
                        data = await tracks_res.json()  # конвертация в json
                        await add_tracks_genre(data, token, session_http, session_db)  # по артисту добавим жанры

                        items = data.get("items",
                                         [])  # Если в data есть ключ "items", то items станет data["items"] иначе items станет пустым списком []
                        all_tracks.extend(items)  # треки с текущей страницы ко всем трекам
                        tracks_url = data.get("next")  # переход на следующую страницу
                        track_params = {}  # next URL уже содержит нужные параметры
                        break  # выход из цикла повторных попыток при успехе
            await session_db.commit()  # делаем commit в бд

    playlist_info["total"] = len(all_tracks)  # добавим количество треков
    playlist_info["tracks"] = {"items": all_tracks}  # добавим треки

    return playlist_info
