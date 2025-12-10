from dotenv import load_dotenv
import os
import base64
from requests import post
import json
import requests
import time
from helpers import get_auth_header

load_dotenv()

spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')


def get_token():
    auth_string = spotify_client_id + ':' + spotify_client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')

    url = "https://accounts.spotify.com/api/token"
    headers = {
        'Authorization': 'Basic ' + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result['access_token']
    return token


def add_tracks_genre(data, token):
    genres = {}
    for track in data["items"]:
        if track["track"] is None:
            continue
        if not (track["track"]["is_local"]):
            artist_id = track["track"]["artists"][0]["id"]
            if artist_id not in genres:
                genres[artist_id] = get_genres_by_artist_id(artist_id, token)
            track["track"]["genres"] = genres[artist_id]


def get_genres_by_artist_id(id, token):
    headers = get_auth_header(token)
    url = f"https://api.spotify.com/v1/artists/{id}"
    fields = "genres"
    params = {"fields": fields}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    return resp.json()["genres"]


def get_tracks_from_playlist_json(playlist_id, token, market="ES"):
    headers = get_auth_header(token)  # headers для запросов

    info_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"  # url
    info_fields = "public,owner(display_name),description,name,id"  # что хочу узнать о плейлисте
    info_params = {
        "market": market,
        "fields": info_fields
    }  # словарь для получения инфы о треках
    playlist_resp = requests.get(info_url, headers=headers, params=info_params)  # get запрос для информации о плейлисте

    try:
        playlist_resp.raise_for_status()  # ошибка если response != 200
    except requests.HTTPError as e:
        if playlist_resp.status_code == 404:
            return None
        else:
            raise e

    playlist_info = playlist_resp.json()  # конвертация в json
    playlist_info["owner"] = playlist_info["owner"]["display_name"]  # упростил структуру словаря

    if playlist_info["public"] == "false":
        return None

    tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # url
    track_fields = "items(track(id,name,artists(id,name),duration_ms,popularity,is_local,album(name))),next"  # что хотим от каждого трека
    track_params = {
        "market": market,
        "fields": track_fields,
        "limit": 100
    }  # параметры для получения треков
    all_tracks = []  # список словарей - треков
    while tracks_url:
        tracks_res = requests.get(tracks_url, headers=headers,
                                  params=track_params)  # запрос на получение треков с текущей страницы

        if tracks_res.status_code == 429:  # если превысили время ожидания
            retry = int(tracks_res.headers.get("Retry-After", "1"))  # время ожидания
            time.sleep(retry)  # ждём
            continue  # следующая попытка

        tracks_res.raise_for_status()  # ошибка если response != 200
        data = tracks_res.json()  # конвертация в json
        add_tracks_genre(data, token)  # по артисту добавим жанры

        items = data.get("items",
                         [])  # Если в data есть ключ "items", то items станет data["items"] инчае items станет пустым списком []
        all_tracks.extend(items)  # треки с текущей страницы ко всем трекам

        tracks_url = data.get("next")  # переход на следующую страницу

    playlist_info["total"] = len(all_tracks)  # добавим количество треков
    playlist_info["tracks"] = {"items": all_tracks}  # добавим треки

    return playlist_info
