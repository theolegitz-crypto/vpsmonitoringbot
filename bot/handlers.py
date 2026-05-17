from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    ALERTS_BUTTON,
    ADD_SERVER_BUTTON,
    CANCEL_BUTTON,
    EXAMPLES_BUTTON,
    HELP_BUTTON,
    SERVERS_BUTTON,
    STATUS_BUTTON,
    cancel_keyboard,
    main_menu_keyboard,
    mute_duration_keyboard,
    server_actions_keyboard,
    server_picker_keyboard,
)
from bot.services import (
    alerts_text,
    create_server_from_bot,
    get_server_detail,
    help_text,
    history_text,
    history_text_by_id,
    normalize_optional_text,
    parse_ports_input,
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
from bot.states import AddServerStates


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


async def start_add_server_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddServerStates.waiting_for_name)
    await message.answer(
        "➕ Добавление сервера\n\nШаг 1 из 6.\nВведите имя сервера.\nПример: `vps-germany-1`",
        reply_markup=cancel_keyboard,
        parse_mode="Markdown",
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


@router.message(Command("addserver"))
async def cmd_addserver(message: Message, state: FSMContext) -> None:
    await start_add_server_flow(message, state)


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
        "/addserver\n"
        "/mute\n"
        "/ssl example.com"
    )


@router.message(F.text == ADD_SERVER_BUTTON)
async def add_server_button(message: Message, state: FSMContext) -> None:
    await start_add_server_flow(message, state)


@router.message(Command("cancel"))
@router.message(F.text == CANCEL_BUTTON)
async def cancel_flow(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if not current_state:
        await message.answer("Нечего отменять.", reply_markup=main_menu_keyboard)
        return
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu_keyboard)


@router.message(AddServerStates.waiting_for_name)
async def add_server_name_step(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи нормальное имя сервера.")
        return
    await state.update_data(name=name)
    await state.set_state(AddServerStates.waiting_for_address)
    await message.answer(
        "Шаг 2 из 6.\nВведите IP или домен сервера.\nПример: `203.0.113.10` или `vps.example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_address)
async def add_server_address_step(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if len(address) < 3:
        await message.answer("Адрес выглядит слишком коротким. Попробуй ещё раз.")
        return
    await state.update_data(address=address)
    await state.set_state(AddServerStates.waiting_for_description)
    await message.answer(
        "Шаг 3 из 6.\nВведите описание сервера или отправь `-`, если описание не нужно.",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_description)
async def add_server_description_step(message: Message, state: FSMContext) -> None:
    await state.update_data(description=normalize_optional_text(message.text))
    await state.set_state(AddServerStates.waiting_for_website_url)
    await message.answer(
        "Шаг 4 из 6.\nВведи URL сайта для HTTP-проверки или `-`, если не нужно.\nПример: `https://example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_website_url)
async def add_server_website_step(message: Message, state: FSMContext) -> None:
    await state.update_data(website_url=normalize_optional_text(message.text))
    await state.set_state(AddServerStates.waiting_for_ports)
    await message.answer(
        "Шаг 5 из 6.\nВведи TCP-порты через запятую или `-`, если не нужно.\nПример: `22,80,443,5432`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_ports)
async def add_server_ports_step(message: Message, state: FSMContext) -> None:
    try:
        ports = parse_ports_input(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(tcp_ports=ports)
    await state.set_state(AddServerStates.waiting_for_ssl_domain)
    await message.answer(
        "Шаг 6 из 6.\nВведи домен для SSL-проверки или `-`, если не нужно.\nПример: `example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_ssl_domain)
async def add_server_ssl_step(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ssl_domain = normalize_optional_text(message.text)

    try:
        server, checks_added = await create_server_from_bot(
            name=data["name"],
            address=data["address"],
            description=data.get("description"),
            website_url=data.get("website_url"),
            tcp_ports=data.get("tcp_ports", []),
            ssl_domain=ssl_domain,
        )
    except ValueError as exc:
        await message.answer(f"❌ Не удалось создать сервер: {exc}", reply_markup=main_menu_keyboard)
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"✅ Сервер `{server.name}` добавлен.\nСоздано проверок: {checks_added}",
        reply_markup=main_menu_keyboard,
        parse_mode="Markdown",
    )

    text = await server_detail_text_by_id(server.id)
    if text:
        detail = await get_server_detail(server.id)
        await message.answer(
            text,
            reply_markup=server_actions_keyboard(server.id, is_muted=detail.muted_until is not None if detail else False),
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
