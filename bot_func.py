import telebot
from dotenv import load_dotenv
import os
from spotify_func import *
from helpers import *

load_dotenv()

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
token = get_token()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Отправь ссылку на плейлист")
    bot.register_next_step_handler(message, get_tracks_url_from_user)


def get_tracks_url_from_user(message):
    try:
        playlist_url = message.text
        try:
            playlist_id = extract_playlist_id(playlist_url)
        except Exception as e:
            bot.reply_to(message, "Неверная ссылка. Отправю новую ссылку")
            bot.register_next_step_handler(message, get_tracks_url_from_user)
            print(f"Ошибка принятия ссылки: {e}")
            return

        prev_message = bot.reply_to(message, "Получаю информацию...")

        playlist_data = get_tracks_from_playlist_json(playlist_id, token)

        if playlist_data is None:
            bot.edit_message_text(chat_id=prev_message.chat.id, message_id=prev_message.message_id, text="Плейлист недоступен")
            return

        if playlist_data["total"] == 0:
            bot.edit_message_text(chat_id=prev_message.chat.id, message_id=prev_message.message_id, text="Ничего не могу сказать про пустой плейлист")
            return

        artists_freq_dictionary = artists_freq(playlist_data)
        most_popular_track_data = most_popular_track(playlist_data)
        albums = albums_count(playlist_data)
        most_popular_track_genres_data = most_popular_genre(playlist_data)
        avg_duration = round(get_avg_duration_ms(playlist_data) / 60000.0, 2)

        with open("tracks.json", "w", encoding="utf-8") as f:
            json.dump(playlist_data, f, ensure_ascii=False, indent=4)

        info_for_message = \
            (f"Название плейлиста: {playlist_data["name"]}\n"
             f"Автор: {playlist_data["owner"]}\n"
             f"Описание: {playlist_data["description"] if len(playlist_data["description"]) > 0 else "без описания"}\n"
             f"Всего {playlist_data["total"]} треков из {albums} альбомов от {len(artists_freq_dictionary)} исполнителей\n"
             f"Самый популярный трек: \"{most_popular_track_data[0]}\"\n"
             f"Самый популярный исполнитель: {max(artists_freq_dictionary, key=artists_freq_dictionary.get)}, треков: {artists_freq_dictionary[max(artists_freq_dictionary, key=artists_freq_dictionary.get)]}\n"
             f"Самый популярный жанр: {most_popular_genre_output(most_popular_track_genres_data)}\n"
             f"Средняя продолжительность трека: {avg_duration} {plural_minutes(avg_duration)}")

        bot.edit_message_text(chat_id=prev_message.chat.id, message_id=prev_message.message_id, text=info_for_message)

    except Exception as e:
        bot.reply_to(message, "Неизвестная ошибка попробуйте ещё раз")
        print(f"Неизвестная ошибка: {e}")
        raise e


@bot.message_handler(func=lambda message: True)
def dont_understand(message):
    bot.reply_to(message, "Прости, я тебя не понимаю. Напиши /start или /help")
