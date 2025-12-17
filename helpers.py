from collections import deque
from lastfm_func import get_list_similar_tracks
import random


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def extract_playlist_id(playlist_url):
    if "https://open.spotify.com/playlist/" in playlist_url:
        playlist_id = (playlist_url.split("/")[-1]).split("?")[0]
        if len(playlist_id) == 22:
            return playlist_id
        else:
            raise ValueError("Invalid playlist URL")
    else:
        raise ValueError("Playlist URL must start with https://open.spotify.com/playlist/")


def artists_freq(data):
    artists = {}
    for track in data["tracks"]["items"]:
        if track["track"] is None:
            continue
        if not (track["track"]["is_local"]):
            track_name = track["track"]["name"]
            for artist in track["track"]["artists"]:
                if artist["name"] not in artists:
                    artists[artist["name"]] = [1, track_name]
                else:
                    artists[artist["name"]][0] += 1

    return artists


def albums_count(data):
    albums = {}
    for track in data["tracks"]["items"]:
        if track["track"] is None:
            continue
        if not (track["track"]["is_local"]):
            album_name = track["track"]["album"]["name"]
            if album_name not in albums:
                albums[album_name] = 1
            else:
                albums[album_name] += 1
    return len(albums)


def most_popular_tracks(data):
    max_len = 5
    top_tracks = deque()
    for track_item in data["tracks"]["items"]:
        track = track_item.get("track")
        if track is None or track.get("is_local"):
            continue
        popularity = track["popularity"]
        track_name = track["name"]
        track_artists = track["artists"][0]["name"]

        if popularity > -1:
            candidate = (popularity, track_name, track_artists)

            if len(top_tracks) < max_len or popularity > top_tracks[0][0]:
                top_tracks.append(candidate)
                if len(top_tracks) > max_len:
                    top_tracks.popleft()

    return sorted(top_tracks, key=lambda x: x[0], reverse=True)


def get_avg_duration_ms(data):
    sum_duration = 0
    for track in data["tracks"]["items"]:
        if track["track"] is None:
            continue
        sum_duration += track["track"]["duration_ms"]

    return sum_duration / data["total"]


def plural_minutes(n):
    n_int = int(round(n))
    if n_int % 10 == 1 and n_int % 100 != 11:
        return "минута"
    if 2 <= n_int % 10 <= 4 and not (12 <= n_int % 100 <= 14):
        return "минуты"
    return "минут"


def most_popular_genre(data):
    genres = {}
    for track in data["tracks"]["items"]:
        if track["track"] is None:
            continue
        if not (track["track"]["is_local"]) and track["track"]["genres"] is not None:
            for genre in track["track"]["genres"]:
                if genre not in genres:
                    genres[genre] = 1
                else:
                    genres[genre] += 1

    return genres


def most_popular_genre_output(data):
    if len(data) == 0:
        return "не удалось узнать жанры треков из плейлиста"
    else:
        return max(data, key=data.get)


async def get_recommendations(most_popular_tracks_data, playlist_data, count=5):
    playlist_track_names = {t["track"]["name"].lower() for t in playlist_data["tracks"]["items"] if t.get("track") and not t["track"].get("is_local")}
    similar_tracks = set(await get_list_similar_tracks(most_popular_tracks_data))
    recommendations = random.sample([track for track in similar_tracks if track.lower() not in playlist_track_names], k=count)
    return recommendations


def extend_mpt_data(data, new):
    if new[2] not in [(t[2]) for t in data]:
        data.append(new)
