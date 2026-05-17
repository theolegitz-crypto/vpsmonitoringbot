from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard
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
        "SwagMonitor is ready.\n\n"
        "Use the buttons below for quick actions.\n"
        "For detailed actions use commands like /server vps1 or /ping vps1.\n\n"
        "If you have not added monitors yet, do it in the web panel first.",
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
        await message.answer("Usage: /server <name>")
        return

    text = await server_detail_text(command.args.strip())
    await message.answer(text or "Server not found")


@router.message(Command("alerts"))
async def cmd_alerts(message: Message) -> None:
    await message.answer(await alerts_text())


@router.message(Command("history"))
async def cmd_history(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /history <name>")
        return

    text = await history_text(command.args.strip())
    await message.answer(text or "Server not found")


@router.message(Command("ports"))
async def cmd_ports(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /ports <name>")
        return

    text = await ports_text(command.args.strip())
    await message.answer(text or "Server not found")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /mute <name> <duration>")
        return

    parts = command.args.strip().split()
    if len(parts) < 2:
        await message.answer("Usage: /mute <name> <duration>")
        return

    name = " ".join(parts[:-1])
    duration = parts[-1]
    try:
        text = await mute_text(name, duration)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await message.answer(text or "Server or check not found")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /unmute <name>")
        return

    text = await unmute_text(command.args.strip())
    await message.answer(text or "Server or check not found")


@router.message(Command("ping"))
async def cmd_ping(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /ping <name>")
        return

    text = await run_ping_text(command.args.strip())
    await message.answer(text or "Server not found")


@router.message(Command("ssl"))
async def cmd_ssl(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /ssl <domain>")
        return

    await message.answer(await run_ssl_text(command.args.strip()))


@router.message(F.text == "Examples")
async def examples_button(message: Message) -> None:
    await message.answer(
        "Examples\n"
        "/status\n"
        "/servers\n"
        "/server vps1\n"
        "/ping vps1\n"
        "/history vps1\n"
        "/ports vps1\n"
        "/mute vps1 2h"
    )
