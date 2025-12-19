from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from spotify_func import get_tracks_from_playlist_json
from helpers import *
from helpers import get_recommendations, save_full_history
from db import create_session, get_user_history, get_playlist_history

load_dotenv()

HISTORY_CHOICE = 1

default_keyboard = ReplyKeyboardMarkup(
    keyboard=[["/start", "/history"]],
    resize_keyboard=True,
    one_time_keyboard=False
)


async def start(update, context):
    await update.message.reply_text("Отправь ссылку на плейлист", reply_markup=default_keyboard)


async def get_tracks_url_from_user(update, context, token):
    try:
        playlist_url = update.message.text
        try:
            playlist_id = extract_playlist_id(playlist_url)
        except Exception as e:
            await update.message.reply_text("Неверная ссылка. Отправь новую ссылку")
            print(f"Ошибка принятия ссылки: {e}")

        prev_message = await update.message.reply_text("Получаю информацию...")

        playlist_data = await get_tracks_from_playlist_json(playlist_id, token)

        if playlist_data is None:
            await prev_message.edit_text("Плейлист недоступен")
            return

        if playlist_data["total"] == 0:
            await prev_message.edit_text("Ничего не могу сказать про пустой плейлист")
            return

        artists_freq_dictionary = artists_freq(playlist_data)
        most_popular_tracks_data = most_popular_tracks(playlist_data)
        albums = albums_count(playlist_data)
        most_popular_track_genres_data = most_popular_genre(playlist_data)
        avg_duration = round(get_avg_duration_ms(playlist_data) / 60000.0, 2)

        description = playlist_data['description'] if len(playlist_data['description']) > 0 else 'без описания'
        max_artist = max(artists_freq_dictionary, key=artists_freq_dictionary.get)

        extend_mpt_data(most_popular_tracks_data, (0, artists_freq_dictionary[max_artist][1], max_artist))
        recommendations = await get_recommendations(most_popular_tracks_data, playlist_data)

        info_for_message = (
            f"🎧 Название: {playlist_data['name']}\n"
            f"👤 Автор: {playlist_data['owner']}\n"
            f"📝 Описание: {description or '—'}\n\n"
            f"📊 Статистика:\n"
            f"• {playlist_data['total']} треков\n"
            f"• {albums} альбомов\n"
            f"• {len(artists_freq_dictionary)} исполнителей\n\n"
            f"🎵 Топ-трек: {most_popular_tracks_data[0][1]}\n"
            f"👑 Топ-исполнитель: {max_artist} ({artists_freq_dictionary[max_artist][0]} треков)\n"
            f"🎸 Топ-жанр: {most_popular_genre_output(most_popular_track_genres_data)}\n"
            f"⏱️ Средняя длительность: {avg_duration} {plural_minutes(avg_duration)}\n\n"
            f"🎁 Рекомендации:\n" + (
                "треков очень много, нечего рекомендовать" if len(recommendations) == 0 else '\n'.join(
                    [f"{i + 1}. {track}" for i, track in enumerate(recommendations)]))
        )

        user_id = str(update.message.chat.id)
        await save_full_history(user_id, playlist_id, info_for_message, playlist_data['name'])
        await prev_message.edit_text(info_for_message)

    except Exception as e:
        await update.message.reply_text("Неизвестная ошибка попробуйте ещё раз")
        print(f"Неизвестная ошибка: {e}")


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


def chunk(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


async def history(update, context):
    user_id = str(update.message.chat.id)

    async with create_session() as session:
        items = await get_user_history(session, user_id)

    if len(items) > 0:
        context.user_data["history_items"] = items

        names = list(items.keys())
        n = len(names)
        if n <= 3:
            per_row = 1
        elif n <= 6:
            per_row = 2
        else:
            per_row = 3

        playlist_buttons = chunk(names, per_row)
        playlist_buttons.append(["/start", "/history", "/cancel"])

        keyboard = ReplyKeyboardMarkup(
            keyboard=playlist_buttons if len(items) > 0 else [["/start", "/history", "/cancel"]],
            resize_keyboard=True,
            one_time_keyboard=False,
        )

        await update.message.reply_text("Выберите название плейлиста для просмотра информации о нём",
                                        reply_markup=keyboard)
        return HISTORY_CHOICE

    else:
        await update.message.reply_text("История пуста. Отправьте ссылку на плейлист",
                                        reply_markup=default_keyboard)
        return ConversationHandler.END


async def history_choice(update, context):
    text = (update.message.text or "").strip()

    items = context.user_data.get("history_items")
    playlist_id = items.get(text)

    if playlist_id is None:
        await update.message.reply_text("Неверное название плейлиста")
        return HISTORY_CHOICE

    async with create_session() as session:
        user_id = str(update.message.chat.id)
        data = await get_playlist_history(session, playlist_id)
        await save_user_history(session, user_id, playlist_id)
        await session.commit()

    await update.message.reply_text(data, reply_markup=default_keyboard)
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Отправь ссылку на плейлист", reply_markup=default_keyboard)
    return ConversationHandler.END
