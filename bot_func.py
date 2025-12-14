from dotenv import load_dotenv
from telegram.ext import ConversationHandler
from spotify_func import get_tracks_from_playlist_json
from helpers import *

load_dotenv()

WAITING_FOR_PLAYLIST = 1


async def start(update, context):
    await update.message.reply_text("Отправь ссылку на плейлист")
    return WAITING_FOR_PLAYLIST


async def get_tracks_url_from_user(update, context, token):
    try:
        playlist_url = update.message.text
        try:
            playlist_id = extract_playlist_id(playlist_url)
        except Exception as e:
            await update.message.reply_text("Неверная ссылка. Отправь новую ссылку")
            print(f"Ошибка принятия ссылки: {e}")
            return WAITING_FOR_PLAYLIST

        prev_message = await update.message.reply_text("Получаю информацию...")

        playlist_data = await get_tracks_from_playlist_json(playlist_id, token)

        if playlist_data is None:
            await prev_message.edit_text("Плейлист недоступен")
            return ConversationHandler.END

        if playlist_data["total"] == 0:
            await prev_message.edit_text("Ничего не могу сказать про пустой плейлист")
            return ConversationHandler.END

        artists_freq_dictionary = artists_freq(playlist_data)
        most_popular_track_data = most_popular_track(playlist_data)
        albums = albums_count(playlist_data)
        most_popular_track_genres_data = most_popular_genre(playlist_data)
        avg_duration = round(get_avg_duration_ms(playlist_data) / 60000.0, 2)

        description = playlist_data['description'] if len(playlist_data['description']) > 0 else 'без описания'
        max_artist = max(artists_freq_dictionary, key=artists_freq_dictionary.get)

        info_for_message = (
            f"Название плейлиста: {playlist_data['name']}\n"
            f"Автор: {playlist_data['owner']}\n"
            f"Описание: {description}\n"
            f"Всего {playlist_data['total']} треков из {albums} альбомов от {len(artists_freq_dictionary)} исполнителей\n"
            f'Самый популярный трек: "{most_popular_track_data[0]}"\n'
            f"Самый популярный исполнитель: {max_artist}, треков: {artists_freq_dictionary[max_artist]}\n"
            f"Самый популярный жанр: {most_popular_genre_output(most_popular_track_genres_data)}\n"
            f"Средняя продолжительность трека: {avg_duration} {plural_minutes(avg_duration)}"
        )

        await prev_message.edit_text(info_for_message)
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text("Неизвестная ошибка попробуйте ещё раз")
        print(f"Неизвестная ошибка: {e}")
        raise e # удалить после релиза!!!

async def error_message(update, context):
    await update.message.reply_text("Неизвестная ошибка попробуйте ещё раз")


async def dont_understand(update, context):
    await update.message.reply_text("Прости, я тебя не понимаю. Напиши /start")


async def any_text_router(update, context, token):
    text = (update.message.text or "").strip()
    try:
        extract_playlist_id(text)
    except Exception:
        await update.message.reply_text("Прости, я тебя не понимаю. Пришли ссылку на плейлист или /start.")
        return

    await get_tracks_url_from_user(update, context, token)