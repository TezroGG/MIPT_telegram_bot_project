from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from bot_func import start, get_tracks_url_from_user, dont_understand, error_message, WAITING_FOR_PLAYLIST
from spotify_func import *
import os
import asyncio
from dotenv import load_dotenv
from telegram.request import HTTPXRequest
from db import global_init

load_dotenv()

spotify_token = None


async def init_all():
    global spotify_token
    await global_init("cache.db")
    spotify_token = await get_token()


async def get_token_wrapper(update, context):
    return await get_tracks_url_from_user(update, context, spotify_token)


async def error_handler(update, context):
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("Временная сетевая ошибка, попробуйте ещё раз.")
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(init_all())

    request = HTTPXRequest(connect_timeout=20, read_timeout=40)
    application = Application.builder().token(os.getenv("BOT_TOKEN")).request(request).concurrent_updates(True).build()

    try:
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler(['start', 'help'], start)],
            states={
                WAITING_FOR_PLAYLIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_token_wrapper)]
            },
            fallbacks=[],
        )

        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dont_understand))
    except Exception as err:
        print(err)
        error_message()

    application.add_error_handler(error_handler)
    application.run_polling()
