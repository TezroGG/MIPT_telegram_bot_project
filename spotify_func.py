from dotenv import load_dotenv
import os
import base64
from requests import post
import json
import requests
import time

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

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def extract_playlist_id(playlist_url):
    if "https://open.spotify.com/playlist/" in playlist_url:
        id = (playlist_url.split("/")[-1]).split("?")[0]
        if len(id) > 0:
            return id
        else:
            raise ValueError("Invalid playlist URL")
    else:
        raise ValueError("Playlist URL must start with https://open.spotify.com/playlist/")

def get_tracks_from_playlist_json(playlist_id, token, market = "ES"):
    headers = {"Authorization": f"Bearer {token}"} # headers for all requests

    info_url = f"https://api.spotify.com/v1/playlists/{playlist_id}" # url for get info about playlist
    info_fields = "public,owner(display_name),description,name,id" # data which I get about playlist
    info_params = {
        "market": market,
        "fields": info_fields
    } # dict to get info about playlist
    playlist_resp = requests.get(info_url, headers=headers, params=info_params) # get-request to collect playlist info
    # try:
    playlist_resp.raise_for_status() # raise error if response != 200
    # except requests.exceptions.HTTPError as err:
    #     print(err)
    #     print(requests.get(info_url, headers=headers, params={
    #     "market": market,
    #     "fields": "error(status, message)"
    #     }).text)
    playlist_info = playlist_resp.json() # turn into json
    playlist_info["owner"] = playlist_info["owner"]["display_name"] # упростил структуру словаря

    tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks" # url for get tracks
    track_fields = "items(track(id,name,artists(id,name),duration_ms,popularity,is_local)),next" # data for each track
    track_params = {
        "market": market,
        "fields": track_fields,
        "limit": 100
    } # dict to get tracks
    all_tracks = [] # array with dicts with all tracks
    while tracks_url:
        tracks_res = requests.get(tracks_url, headers=headers, params=track_params) # get-request to collect tracks on current page

        if tracks_res.status_code == 429: # if the app has exceeded its rate limits
            retry = int(tracks_res.headers.get("Retry-After", "1")) # время ожидания
            time.sleep(retry) # ждём
            continue # следующая попытка

        tracks_res.raise_for_status() # raise error if response != 200
        data = tracks_res.json() # turn into json
        items = data.get("items", []) # Если в data есть ключ "items", то items станет data["items"] инчае items станет пустым списком []
        all_tracks.extend(items) # add tracks from current page to all tracks

        tracks_url = data.get("next") # go to the next page

    playlist_info["total"] = len(all_tracks) # get total count of tracks and add to playlist_info
    playlist_info["tracks"] = {"items": all_tracks} # add tracks to playlist_info

    return playlist_info


last_fm_api_key = os.getenv('LAST_FM_API_KEY')
last_fm_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
last_fm_url = os.getenv('LAST_FM_URL')

def get_track_info(track_name, artist_name):
    params = {
        "method": "track.gettoptags",
        "artist": artist_name,
        "track": track_name,
        "api_key": last_fm_api_key,
        "format": "json",
        "autocorrect": 1
    }
    resp = requests.get(last_fm_url, params=params)
    resp.raise_for_status()
    return resp.json()