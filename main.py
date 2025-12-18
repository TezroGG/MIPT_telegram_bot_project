from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from bot_func import start, any_text_router, history, HISTORY_CHOICE, cancel, history_choice
from spotify_func import get_token
import os
import asyncio
from dotenv import load_dotenv
from telegram.request import HTTPXRequest
from db import db_init

load_dotenv()

spotify_token = None


async def init_all():
    global spotify_token
    await db_init("cache.db")
    spotify_token = await get_token()


async def any_text_router_wrapper(update, context):
    return await any_text_router(update, context, spotify_token)


if __name__ == '__main__':
    asyncio.run(init_all())
    print("Bot start")

    request = HTTPXRequest(connect_timeout=20, read_timeout=40)
    application = (
        Application.builder().token(os.getenv("BOT_TOKEN")).request(request).concurrent_updates(True).build())

    application.add_handler(CommandHandler(['start', 'help'], start))

    conv_history = ConversationHandler(
        entry_points=[CommandHandler("history", history)],
        states={
            HISTORY_CHOICE: [
                CommandHandler("cancel", cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, history_choice),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_history)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_text_router_wrapper))

    application.run_polling()
