from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    ALERTS_BUTTON,
    EXAMPLES_BUTTON,
    HELP_BUTTON,
    SERVERS_BUTTON,
    STATUS_BUTTON,
    main_menu_keyboard,
    mute_duration_keyboard,
    server_actions_keyboard,
    server_picker_keyboard,
)
from bot.services import (
    alerts_text,
    get_server_detail,
    help_text,
    history_text,
    history_text_by_id,
    list_servers_for_picker,
    mute_text,
    mute_text_by_id,
    ports_text,
    ports_text_by_id,
    run_ping_text,
    run_ping_text_by_id,
    run_ssl_text,
    server_detail_text,
    server_detail_text_by_id,
    servers_text,
    status_summary_text,
    unmute_text,
    unmute_text_by_id,
)


router = Router()


ACTION_TITLES = {
    "detail": "🖥 Выбери сервер",
    "ping": "📡 Выбери сервер для ping",
    "history": "🕓 Выбери сервер для истории",
    "ports": "🔌 Выбери сервер для проверки портов",
    "mute": "🔕 Выбери сервер, чтобы приглушить уведомления",
    "unmute": "🔔 Выбери сервер, чтобы включить уведомления",
}


async def send_server_picker(message: Message, action: str, page: int = 0) -> None:
    servers = await list_servers_for_picker()
    if not servers:
        await message.answer("📭 Пока нет добавленных серверов. Сначала создай их в веб-панели.")
        return
    await message.answer(
        ACTION_TITLES[action],
        reply_markup=server_picker_keyboard(servers, action, page),
    )


async def edit_server_picker(callback: CallbackQuery, action: str, page: int = 0) -> None:
    servers = await list_servers_for_picker()
    if not servers:
        await callback.message.edit_text("📭 Пока нет добавленных серверов.")
        return
    await callback.message.edit_text(
        ACTION_TITLES[action],
        reply_markup=server_picker_keyboard(servers, action, page),
    )


async def render_server_detail(callback: CallbackQuery, server_id: int) -> None:
    detail = await get_server_detail(server_id)
    if not detail:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    text = await server_detail_text_by_id(server_id)
    await callback.message.edit_text(
        text,
        reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None),
    )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 SwagMonitor готов к работе.\n\n"
        "Теперь серверы можно выбирать кнопками, без ручного ввода имени.\n"
        "Открой «🖥 Серверы» или используй команды /server, /ping, /history, /ports.\n\n"
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
    await send_server_picker(message, "detail")


@router.message(Command("server"))
async def cmd_server(message: Message, command: CommandObject) -> None:
    if command.args:
        text = await server_detail_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "detail")


@router.message(Command("alerts"))
async def cmd_alerts(message: Message) -> None:
    await message.answer(await alerts_text())


@router.message(Command("history"))
async def cmd_history(message: Message, command: CommandObject) -> None:
    if command.args:
        text = await history_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "history")


@router.message(Command("ports"))
async def cmd_ports(message: Message, command: CommandObject) -> None:
    if command.args:
        text = await ports_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "ports")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if command.args:
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
        return
    await send_server_picker(message, "mute")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, command: CommandObject) -> None:
    if command.args:
        text = await unmute_text(command.args.strip())
        await message.answer(text or "❌ Сервер или проверка не найдены")
        return
    await send_server_picker(message, "unmute")


@router.message(Command("ping"))
async def cmd_ping(message: Message, command: CommandObject) -> None:
    if command.args:
        text = await run_ping_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "ping")


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
    await send_server_picker(message, "detail")


@router.message(F.text == ALERTS_BUTTON)
async def alerts_button(message: Message) -> None:
    await message.answer(await alerts_text())


@router.message(F.text == HELP_BUTTON)
async def help_button(message: Message) -> None:
    await message.answer(help_text(), reply_markup=main_menu_keyboard)


@router.message(F.text == EXAMPLES_BUTTON)
async def examples_button(message: Message) -> None:
    await message.answer(
        "📚 Примеры\n"
        "/status\n"
        "/servers\n"
        "/server\n"
        "/ping\n"
        "/history\n"
        "/ports\n"
        "/mute\n"
        "/ssl example.com"
    )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "action:status")
async def status_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(await status_summary_text())
    await callback.answer()


@router.callback_query(F.data == "action:alerts")
async def alerts_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(await alerts_text())
    await callback.answer()


@router.callback_query(F.data.startswith("picker:"))
async def picker_callback(callback: CallbackQuery) -> None:
    _, action, page = callback.data.split(":")
    await edit_server_picker(callback, action, int(page))
    await callback.answer()


@router.callback_query(F.data.startswith("server:"))
async def server_action_callback(callback: CallbackQuery) -> None:
    _, action, server_id_raw = callback.data.split(":")
    server_id = int(server_id_raw)

    if action == "detail":
        await render_server_detail(callback, server_id)
    elif action == "ping":
        text = await run_ping_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        detail = await get_server_detail(server_id)
        await callback.message.edit_text(
            text,
            reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None if detail else False),
        )
    elif action == "history":
        text = await history_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        detail = await get_server_detail(server_id)
        await callback.message.edit_text(
            text,
            reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None if detail else False),
        )
    elif action == "ports":
        text = await ports_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        detail = await get_server_detail(server_id)
        await callback.message.edit_text(
            text,
            reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None if detail else False),
        )
    elif action in {"mute", "muteprompt"}:
        detail = await get_server_detail(server_id)
        if not detail:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"🔕 Выбери, на сколько приглушить уведомления для {detail.name}",
            reply_markup=mute_duration_keyboard(server_id),
        )
    elif action == "unmute":
        text = await unmute_text_by_id(server_id)
        detail = await get_server_detail(server_id)
        if not text or not detail:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"{text}\n\n" + (await server_detail_text_by_id(server_id)),
            reply_markup=server_actions_keyboard(server_id, is_muted=False),
        )
    else:
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data.startswith("mute:"))
async def mute_duration_callback(callback: CallbackQuery) -> None:
    _, server_id_raw, duration = callback.data.split(":")
    server_id = int(server_id_raw)

    try:
        text = await mute_text_by_id(server_id, duration)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    detail = await get_server_detail(server_id)
    if not text or not detail:
        await callback.answer("Сервер не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"{text}\n\n" + (await server_detail_text_by_id(server_id)),
        reply_markup=server_actions_keyboard(server_id, is_muted=True),
    )
    await callback.answer()
