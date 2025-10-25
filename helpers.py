from last_fm_func import *


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def extract_playlist_id(playlist_url):
    if "https://open.spotify.com/playlist/" in playlist_url:
        playlist_id = (playlist_url.split("/")[-1]).split("?")[0]
        if len(playlist_id) > 0:
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
            for artist in track["track"]["artists"]:
                if artist["name"] not in artists:
                    artists[artist["name"]] = 1
                else:
                    artists[artist["name"]] += 1

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


def most_popular_track(data):
    track = ""
    popularity = 0
    for track in data["tracks"]["items"]:
        if track["track"] is None:
            continue
        if not (track["track"]["is_local"]) and track["track"]["popularity"] > popularity:
            popularity = track["track"]["popularity"]
        track = track["track"]["name"]

    return track, popularity


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
        if not (track["track"]["is_local"]):
            for genre in track["track"]["genres"]:
                if genre not in genres:
                    genres[genre] = 1
                else:
                    genres[genre] += 1

    return genres


def most_popular_genre_output(data):
    if len(data) == 0:
        return "не удалось узанать жанры треков из плейлиста"
    else:
        return max(data, key=data.get)
