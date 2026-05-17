import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from backend.app.core.config import settings
from bot.handlers import router


logging.basicConfig(level=logging.INFO)


BOT_COMMANDS = [
    BotCommand(command="start", description="Открыть меню"),
    BotCommand(command="help", description="Справка по командам"),
    BotCommand(command="status", description="Общий статус мониторинга"),
    BotCommand(command="servers", description="Список серверов"),
    BotCommand(command="server", description="Подробности по серверу"),
    BotCommand(command="ping", description="Проверить ping прямо сейчас"),
    BotCommand(command="history", description="История статусов"),
    BotCommand(command="ports", description="TCP, HTTP и SSL проверки"),
    BotCommand(command="alerts", description="Последние алерты"),
    BotCommand(command="mute", description="Отключить уведомления"),
    BotCommand(command="unmute", description="Включить уведомления"),
    BotCommand(command="ssl", description="Проверить SSL сертификат"),
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
