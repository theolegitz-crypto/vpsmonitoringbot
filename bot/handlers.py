from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.keyboards import (
    ALERTS_BUTTON,
    EXAMPLES_BUTTON,
    HELP_BUTTON,
    SERVERS_BUTTON,
    STATUS_BUTTON,
    main_menu_keyboard,
)
from bot.services import (
    alerts_text,
    help_text,
    history_text,
    mute_text,
    ports_text,
    run_ping_text,
    run_ssl_text,
    server_detail_text,
    servers_text,
    status_summary_text,
    unmute_text,
)


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 SwagMonitor готов к работе.\n\n"
        "Ниже есть кнопки для быстрых действий.\n"
        "Для точечных запросов используй команды вроде /server vps1 или /ping vps1.\n\n"
        "Если мониторы ещё не добавлены, сначала создай их в веб-панели.",
        reply_markup=main_menu_keyboard,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(help_text(), reply_markup=main_menu_keyboard)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer(await status_summary_text())


@router.message(Command("servers"))
async def cmd_servers(message: Message) -> None:
    await message.answer(await servers_text())


@router.message(Command("server"))
async def cmd_server(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /server <name>")
        return

    text = await server_detail_text(command.args.strip())
    await message.answer(text or "❌ Сервер не найден")


@router.message(Command("alerts"))
async def cmd_alerts(message: Message) -> None:
    await message.answer(await alerts_text())


@router.message(Command("history"))
async def cmd_history(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /history <name>")
        return

    text = await history_text(command.args.strip())
    await message.answer(text or "❌ Сервер не найден")


@router.message(Command("ports"))
async def cmd_ports(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /ports <name>")
        return

    text = await ports_text(command.args.strip())
    await message.answer(text or "❌ Сервер не найден")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /mute <name> <duration>")
        return

    parts = command.args.strip().split()
    if len(parts) < 2:
        await message.answer("Использование: /mute <name> <duration>")
        return

    name = " ".join(parts[:-1])
    duration = parts[-1]
    try:
        text = await mute_text(name, duration)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await message.answer(text or "❌ Сервер или проверка не найдены")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /unmute <name>")
        return

    text = await unmute_text(command.args.strip())
    await message.answer(text or "❌ Сервер или проверка не найдены")


@router.message(Command("ping"))
async def cmd_ping(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /ping <name>")
        return

    text = await run_ping_text(command.args.strip())
    await message.answer(text or "❌ Сервер не найден")


@router.message(Command("ssl"))
async def cmd_ssl(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /ssl <domain>")
        return

    await message.answer(await run_ssl_text(command.args.strip()))


@router.message(F.text == STATUS_BUTTON)
async def status_button(message: Message) -> None:
    await message.answer(await status_summary_text())


@router.message(F.text == SERVERS_BUTTON)
async def servers_button(message: Message) -> None:
    await message.answer(await servers_text())


@router.message(F.text == ALERTS_BUTTON)
async def alerts_button(message: Message) -> None:
    await message.answer(await alerts_text())


@router.message(F.text == HELP_BUTTON)
async def help_button(message: Message) -> None:
    await message.answer(help_text(), reply_markup=main_menu_keyboard)


@router.message(F.text == EXAMPLES_BUTTON)
async def examples_button(message: Message) -> None:
    await message.answer(
        "📚 Примеры команд\n"
        "/status\n"
        "/servers\n"
        "/server vps1\n"
        "/ping vps1\n"
        "/history vps1\n"
        "/ports vps1\n"
        "/mute vps1 2h"
    )
