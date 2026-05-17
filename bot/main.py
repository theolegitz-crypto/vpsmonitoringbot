import asyncio
import logging

from aiogram import Bot, Dispatcher

from backend.app.core.config import settings
from bot.handlers import router


logging.basicConfig(level=logging.INFO)


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    async with Bot(token=settings.telegram_bot_token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
