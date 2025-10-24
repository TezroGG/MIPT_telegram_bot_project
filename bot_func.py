import telebot
from dotenv import load_dotenv
import os
from spotify_func import *

load_dotenv()

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
token = get_token()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Отправь ссылку на плейлист")
	bot.register_next_step_handler(message, get_tracks_url_from_user)

def get_tracks_url_from_user(message):
	playlist_url = message.text
	try:
		playlist_id = extract_playlist_id(playlist_url)
	except:
		bot.reply_to(message, "Неверная ссылка. Отправю новую ссылку")
		bot.register_next_step_handler(message, get_tracks_url_from_user)
		return
	playlist_data = get_tracks_from_playlist_json(playlist_id, token)

	most_popular_artist_data = most_popular_artist(playlist_data)
	most_popular_track_data = most_popular_track(playlist_data)

	# with open("tracks.json", "w", encoding="utf-8") as f:
	# 	json.dump(playlist_data, f, ensure_ascii=False, indent=4)

	info_for_message = \
	(f"Название плейлиста: {playlist_data["name"]}\n"
	 f"Автор: {playlist_data["owner"]}\n"
	 f"Описание: {playlist_data["description"] if len(playlist_data["description"]) > 0 else "без описания"}\n"
	 f"Всего {playlist_data["total"]} треков\n"
	 f"Самый популярный трек: {most_popular_track_data[0]}\n"
	 f"Самый популярный исполнитель: {most_popular_artist_data[0]}, {most_popular_artist_data[1]} - треков")

	bot.reply_to(message, info_for_message)

def most_popular_artist(data):
	artists = {}
	for track in data["tracks"]["items"]:
		for artist in track["track"]["artists"]:
			if artist["name"] not in artists: artists[artist["name"]] = 1
			else: artists[artist["name"]] += 1

	return (max(artists, key=artists.get), artists[max(artists, key=artists.get)])

def most_popular_track(data):
	track = ""
	popularity = 0
	for track in data["tracks"]["items"]:
		if track["track"]["popularity"] > popularity: popularity = track["track"]["popularity"]
		track = track["track"]["name"]

	return (track, popularity)


@bot.message_handler(func=lambda message: True)
def dont_understand(message):
	bot.reply_to(message, "Прости, я тебя не понимаю. Напиши /start или /help")