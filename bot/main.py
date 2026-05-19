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
    BotCommand(command="chatinfo", description="Показать chat id и topic id"),
    BotCommand(command="status", description="Общий статус мониторинга"),
    BotCommand(command="servers", description="Список серверов и кнопки выбора"),
    BotCommand(command="server", description="Выбрать сервер и открыть детали"),
    BotCommand(command="editserver", description="Выбрать сервер и изменить настройки"),
    BotCommand(command="ping", description="Выбрать сервер и проверить ping"),
    BotCommand(command="history", description="Выбрать сервер и открыть историю"),
    BotCommand(command="ports", description="Выбрать сервер и показать порты"),
    BotCommand(command="metrics", description="Собрать и показать SSH-метрики"),
    BotCommand(command="containers", description="Показать Docker-контейнеры по SSH"),
    BotCommand(command="speed", description="Выбрать сервер и запустить speed test по SSH"),
    BotCommand(command="speedlast", description="Показать последний speed test"),
    BotCommand(command="speedhistory", description="История speed test по серверу"),
    BotCommand(command="addserver", description="Добавить сервер через Telegram"),
    BotCommand(command="alerts", description="Последние алерты"),
    BotCommand(command="mute", description="Выбрать сервер и приглушить алерты"),
    BotCommand(command="unmute", description="Выбрать сервер и включить алерты"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
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
