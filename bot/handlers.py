from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services import (
    alerts_text,
    history_text,
    mute_text,
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
        "SwagMonitor bot is ready.\n"
        "Commands: /status, /servers, /server <name>, /alerts, /history <name>, /mute <name> <duration>, /unmute <name>, /ping <name>, /ssl <domain>"
    )


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

