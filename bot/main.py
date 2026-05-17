import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from backend.app.core.config import settings
from bot.handlers import router


logging.basicConfig(level=logging.INFO)


BOT_COMMANDS = [
    BotCommand(command="start", description="Show main menu"),
    BotCommand(command="help", description="How to use the bot"),
    BotCommand(command="status", description="Global status of all monitors"),
    BotCommand(command="servers", description="List configured servers"),
    BotCommand(command="server", description="Details for one server"),
    BotCommand(command="ping", description="Run ping check now"),
    BotCommand(command="history", description="Recent status history"),
    BotCommand(command="ports", description="Show TCP, HTTP and SSL checks"),
    BotCommand(command="alerts", description="Last alert events"),
    BotCommand(command="mute", description="Mute alerts for a monitor"),
    BotCommand(command="unmute", description="Unmute alerts"),
    BotCommand(command="ssl", description="Check SSL certificate"),
]


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    async with Bot(token=settings.telegram_bot_token) as bot:
        await bot.set_my_commands(BOT_COMMANDS)
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
