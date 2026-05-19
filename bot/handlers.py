from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.access import describe_telegram_context, ensure_callback_allowed, ensure_message_allowed
from bot.keyboards import (
    ALERTS_BUTTON,
    ADD_SERVER_BUTTON,
    CANCEL_BUTTON,
    EXAMPLES_BUTTON,
    HELP_BUTTON,
    SERVERS_BUTTON,
    STATUS_BUTTON,
    cancel_inline_keyboard,
    cancel_keyboard,
    main_menu_inline_keyboard,
    main_menu_keyboard,
    mute_duration_keyboard,
    server_actions_keyboard,
    server_delete_confirm_keyboard,
    server_edit_field_keyboard,
    server_picker_keyboard,
)
from bot.services import (
    alerts_text,
    containers_text,
    containers_text_by_id,
    create_server_from_bot,
    delete_server_by_id,
    get_server_detail,
    get_server_edit_field_meta,
    history_text,
    history_text_by_id,
    latest_speed_test_text,
    latest_speed_test_text_by_id,
    list_servers_for_picker,
    metrics_text,
    metrics_text_by_id,
    mute_text,
    mute_text_by_id,
    normalize_optional_text,
    parse_ports_input,
    ports_text,
    ports_text_by_id,
    run_ping_text,
    run_ping_text_by_id,
    run_ssl_text,
    server_detail_text,
    server_detail_text_by_id,
    servers_text,
    speed_test_history_text,
    speed_test_history_text_by_id,
    speed_test_text,
    speed_test_text_by_id,
    status_summary_text,
    unmute_text,
    unmute_text_by_id,
    update_server_field_by_id,
)
from bot.states import AddServerStates, EditServerStates


router = Router()


ACTION_TITLES = {
    "detail": "🖥 Выбери сервер",
    "edit": "✏️ Выбери сервер для редактирования",
    "ping": "📡 Выбери сервер для ping",
    "history": "🕓 Выбери сервер для истории",
    "ports": "🔌 Выбери сервер для портов",
    "speed": "⚡ Выбери сервер для speed test",
    "speedlast": "📶 Выбери сервер для последнего speed test",
    "speedhistory": "📈 Выбери сервер для истории speed test",
    "metrics": "🧠 Выбери сервер для SSH-метрик",
    "containers": "🐳 Выбери сервер для Docker-контейнеров",
    "mute": "🔕 Выбери сервер, чтобы приглушить уведомления",
    "unmute": "🔔 Выбери сервер, чтобы включить уведомления",
}


EXAMPLES_TEXT = (
    "📚 Примеры\n"
    "/status\n"
    "/servers\n"
    "/server\n"
    "/editserver\n"
    "/ping\n"
    "/history\n"
    "/ports\n"
    "/metrics\n"
    "/containers\n"
    "/speed\n"
    "/speedlast\n"
    "/speedhistory\n"
    "/addserver\n"
    "/mute\n"
    "/chatinfo\n"
    "/ssl example.com"
)


HELP_TEXT = (
    "🤖 Команды SwagMonitor\n\n"
    "/status - общий статус всех мониторов\n"
    "/servers - список серверов с выбором кнопками\n"
    "/server - выбрать сервер и открыть подробности\n"
    "/ping - выбрать сервер и запустить ping\n"
    "/history - выбрать сервер и открыть историю доступности\n"
    "/ports - выбрать сервер и посмотреть TCP, HTTP и SSL\n"
    "/metrics - собрать и показать SSH-метрики VPS\n"
    "/containers - собрать и показать Docker-контейнеры по SSH\n"
    "/speed - выбрать сервер и запустить speed test по SSH\n"
    "/speedlast - показать последний speed test без новой постановки в очередь\n"
    "/speedhistory - история speed test по серверу\n"
    "/alerts - последние события и алерты\n"
    "/addserver - добавить сервер прямо через Telegram\n"
    "/mute - приглушить уведомления для сервера\n"
    "/unmute - снова включить уведомления\n"
    "/chatinfo - показать chat id и topic id\n"
    "/ssl <domain> - вручную проверить сертификат\n\n"
    "История: 🟩 OK  🟨 деградация  🟥 сбой  ⬜ нет данных"
)


def menu_markup_for(message: Message):
    return main_menu_keyboard if message.chat.type == "private" else main_menu_inline_keyboard


def cancel_markup_for(message: Message):
    return cancel_keyboard if message.chat.type == "private" else cancel_inline_keyboard


async def send_server_picker(message: Message, action: str, page: int = 0) -> None:
    servers = await list_servers_for_picker()
    if not servers:
        await message.answer(
            "📭 Пока нет добавленных серверов. Сначала создай их в веб-панели или через /addserver.",
            reply_markup=menu_markup_for(message),
        )
        return
    await message.answer(ACTION_TITLES[action], reply_markup=server_picker_keyboard(servers, action, page))


async def edit_server_picker(callback: CallbackQuery, action: str, page: int = 0) -> None:
    if not await ensure_callback_allowed(callback):
        return
    servers = await list_servers_for_picker()
    if not servers:
        await callback.message.edit_text("📭 Пока нет добавленных серверов.", reply_markup=main_menu_inline_keyboard)
        return
    await callback.message.edit_text(
        ACTION_TITLES[action],
        reply_markup=server_picker_keyboard(servers, action, page),
    )


async def render_server_detail(callback: CallbackQuery, server_id: int) -> None:
    if not await ensure_callback_allowed(callback):
        return
    detail = await get_server_detail(server_id)
    if not detail:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    text = await server_detail_text_by_id(server_id)
    await callback.message.edit_text(
        text,
        reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None),
    )


async def render_server_action_text(callback: CallbackQuery, server_id: int, text: str) -> None:
    detail = await get_server_detail(server_id)
    await callback.message.edit_text(
        text,
        reply_markup=server_actions_keyboard(server_id, is_muted=detail.muted_until is not None if detail else False),
    )


async def start_add_server_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddServerStates.waiting_for_name)
    await message.answer(
        "➕ Добавление сервера\n\n"
        "Шаг 1 из 6.\n"
        "Введи имя сервера.\n"
        "Пример: `vps-germany-1`",
        reply_markup=cancel_markup_for(message),
        parse_mode="Markdown",
    )


async def start_edit_server_field_flow(
    *,
    message: Message,
    state: FSMContext,
    server_id: int,
    field: str,
) -> None:
    meta = get_server_edit_field_meta(field)
    await state.clear()
    await state.set_state(EditServerStates.waiting_for_value)
    await state.update_data(server_id=server_id, field=field)
    await message.answer(
        f"✏️ Редактирование поля: {meta['label']}\n\n{meta['prompt']}",
        reply_markup=cancel_markup_for(message),
        parse_mode="Markdown",
    )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    if message.chat.type != "private":
        await message.answer(
            "Убираю старую reply-клавиатуру. В группах и topics используем inline-кнопки.",
            reply_markup=ReplyKeyboardRemove(),
        )
    await message.answer(
        "👋 SwagMonitor готов к работе.\n\n"
        "В личке можно пользоваться кнопками меню, а в группах и topics меню работает через inline-кнопки.\n"
        "Открой «🖥 Серверы» или используй /server, /metrics, /containers, /speed, /ping, /history, /ports.\n\n"
        "Если мониторинг ещё не настроен, сначала добавь сервер через /addserver или из веб-панели.",
        reply_markup=menu_markup_for(message),
    )


@router.message(Command("chatinfo"))
async def cmd_chatinfo(message: Message) -> None:
    await message.answer(
        describe_telegram_context(
            chat_id=message.chat.id,
            chat_type=message.chat.type,
            message_thread_id=getattr(message, "message_thread_id", None),
        ),
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await message.answer(HELP_TEXT, reply_markup=menu_markup_for(message))


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await message.answer(await status_summary_text())


@router.message(Command("servers"))
async def cmd_servers(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await message.answer(await servers_text())
    await send_server_picker(message, "detail")


@router.message(Command("editserver"))
async def cmd_editserver(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await send_server_picker(message, "edit")


@router.message(Command("addserver"))
async def cmd_addserver(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    await start_add_server_flow(message, state)


@router.message(Command("server"))
async def cmd_server(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await server_detail_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "detail")


@router.message(Command("alerts"))
async def cmd_alerts(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await message.answer(await alerts_text())


@router.message(Command("history"))
async def cmd_history(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await history_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "history")


@router.message(Command("ports"))
async def cmd_ports(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await ports_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "ports")


@router.message(Command("metrics"))
async def cmd_metrics(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await metrics_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "metrics")


@router.message(Command("containers"))
async def cmd_containers(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await containers_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "containers")


@router.message(Command("speed"))
async def cmd_speed(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await speed_test_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "speed")


@router.message(Command("speedlast"))
async def cmd_speedlast(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await latest_speed_test_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "speedlast")


@router.message(Command("speedhistory"))
async def cmd_speedhistory(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await speed_test_history_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "speedhistory")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
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
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await unmute_text(command.args.strip())
        await message.answer(text or "❌ Сервер или проверка не найдены")
        return
    await send_server_picker(message, "unmute")


@router.message(Command("ping"))
async def cmd_ping(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        text = await run_ping_text(command.args.strip())
        await message.answer(text or "❌ Сервер не найден")
        return
    await send_server_picker(message, "ping")


@router.message(Command("ssl"))
async def cmd_ssl(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if not command.args:
        await message.answer("Использование: /ssl <domain>")
        return
    await message.answer(await run_ssl_text(command.args.strip()))


@router.message(F.text == STATUS_BUTTON)
async def status_button(message: Message) -> None:
    await cmd_status(message)


@router.message(F.text == SERVERS_BUTTON)
async def servers_button(message: Message) -> None:
    await cmd_servers(message)


@router.message(F.text == ALERTS_BUTTON)
async def alerts_button(message: Message) -> None:
    await cmd_alerts(message)


@router.message(F.text == HELP_BUTTON)
async def help_button(message: Message) -> None:
    await cmd_help(message)


@router.message(F.text == EXAMPLES_BUTTON)
async def examples_button(message: Message) -> None:
    if not await ensure_message_allowed(message):
        return
    await message.answer(EXAMPLES_TEXT, reply_markup=menu_markup_for(message))


@router.message(F.text == ADD_SERVER_BUTTON)
async def add_server_button(message: Message, state: FSMContext) -> None:
    await cmd_addserver(message, state)


@router.message(Command("cancel"))
@router.message(F.text == CANCEL_BUTTON)
async def cancel_flow(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    current_state = await state.get_state()
    if not current_state:
        await message.answer("Нечего отменять.", reply_markup=menu_markup_for(message))
        return
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=menu_markup_for(message))


@router.message(AddServerStates.waiting_for_name)
async def add_server_name_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введи нормальное имя сервера.")
        return
    await state.update_data(name=name)
    await state.set_state(AddServerStates.waiting_for_address)
    await message.answer(
        "Шаг 2 из 6.\n"
        "Введи IP или домен сервера.\n"
        "Пример: `203.0.113.10` или `vps.example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_address)
async def add_server_address_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    address = (message.text or "").strip()
    if len(address) < 3:
        await message.answer("Адрес выглядит слишком коротким. Попробуй ещё раз.")
        return
    await state.update_data(address=address)
    await state.set_state(AddServerStates.waiting_for_description)
    await message.answer(
        "Шаг 3 из 6.\n"
        "Введи описание сервера или отправь `-`, если описание не нужно.",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_description)
async def add_server_description_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    await state.update_data(description=normalize_optional_text(message.text or ""))
    await state.set_state(AddServerStates.waiting_for_website_url)
    await message.answer(
        "Шаг 4 из 6.\n"
        "Введи URL сайта для HTTP-проверки или `-`, если не нужно.\n"
        "Пример: `https://example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_website_url)
async def add_server_website_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    await state.update_data(website_url=normalize_optional_text(message.text or ""))
    await state.set_state(AddServerStates.waiting_for_ports)
    await message.answer(
        "Шаг 5 из 6.\n"
        "Введи TCP-порты через запятую или `-`, если не нужно.\n"
        "Пример: `22,80,443,5432`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_ports)
async def add_server_ports_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    try:
        ports = parse_ports_input(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(tcp_ports=ports)
    await state.set_state(AddServerStates.waiting_for_ssl_domain)
    await message.answer(
        "Шаг 6 из 6.\n"
        "Введи домен для SSL-проверки или `-`, если не нужно.\n"
        "Пример: `example.com`",
        parse_mode="Markdown",
    )


@router.message(AddServerStates.waiting_for_ssl_domain)
async def add_server_ssl_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return
    data = await state.get_data()
    ssl_domain = normalize_optional_text(message.text or "")

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
        await message.answer(
            f"❌ Не удалось создать сервер: {exc}",
            reply_markup=menu_markup_for(message),
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(
        f"✅ Сервер `{server.name}` добавлен.\nСоздано проверок: {checks_added}",
        reply_markup=menu_markup_for(message),
        parse_mode="Markdown",
    )

    text = await server_detail_text_by_id(server.id)
    if text:
        detail = await get_server_detail(server.id)
        await message.answer(
            text,
            reply_markup=server_actions_keyboard(server.id, is_muted=detail.muted_until is not None if detail else False),
        )


@router.message(EditServerStates.waiting_for_value)
async def edit_server_value_step(message: Message, state: FSMContext) -> None:
    if not await ensure_message_allowed(message):
        return

    data = await state.get_data()
    server_id = data.get("server_id")
    field = data.get("field")
    if not server_id or not field:
        await state.clear()
        await message.answer(
            "❌ Сессия редактирования потеряна. Открой сервер заново.",
            reply_markup=menu_markup_for(message),
        )
        return

    try:
        updated = await update_server_field_by_id(int(server_id), field, message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return

    if not updated:
        await state.clear()
        await message.answer("❌ Сервер не найден.", reply_markup=menu_markup_for(message))
        return

    meta = get_server_edit_field_meta(field)
    await state.clear()
    await message.answer(
        f"✅ Поле «{meta['label']}» обновлено для сервера {updated.name}.",
        reply_markup=menu_markup_for(message),
    )

    text = await server_detail_text_by_id(updated.id)
    detail = await get_server_detail(updated.id)
    if text and detail:
        await message.answer(
            text,
            reply_markup=server_actions_keyboard(updated.id, is_muted=detail.muted_until is not None),
        )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "action:status")
async def status_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await callback.message.edit_text(await status_summary_text(), reply_markup=main_menu_inline_keyboard)
    await callback.answer()


@router.callback_query(F.data == "action:alerts")
async def alerts_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await callback.message.edit_text(await alerts_text(), reply_markup=main_menu_inline_keyboard)
    await callback.answer()


@router.callback_query(F.data == "action:servers")
async def servers_callback(callback: CallbackQuery) -> None:
    await edit_server_picker(callback, "detail")
    await callback.answer()


@router.callback_query(F.data == "action:help")
async def help_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await callback.message.edit_text(HELP_TEXT, reply_markup=main_menu_inline_keyboard)
    await callback.answer()


@router.callback_query(F.data == "action:examples")
async def examples_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await callback.message.edit_text(EXAMPLES_TEXT, reply_markup=main_menu_inline_keyboard)
    await callback.answer()


@router.callback_query(F.data == "action:addserver")
async def add_server_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await start_add_server_flow(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "action:cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_callback_allowed(callback):
        return
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=main_menu_inline_keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("picker:"))
async def picker_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    _, action, page = callback.data.split(":")
    await edit_server_picker(callback, action, int(page))
    await callback.answer()


@router.callback_query(F.data.startswith("editfield:"))
async def edit_field_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_callback_allowed(callback):
        return
    _, server_id_raw, field = callback.data.split(":")
    await start_edit_server_field_flow(
        message=callback.message,
        state=state,
        server_id=int(server_id_raw),
        field=field,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("deleteconfirm:"))
async def delete_confirm_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    _, server_id_raw = callback.data.split(":")
    server_id = int(server_id_raw)
    deleted_name = await delete_server_by_id(server_id)
    if not deleted_name:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Сервер {deleted_name} удалён.\n\nОткрой /servers, чтобы выбрать другой сервер.",
        reply_markup=main_menu_inline_keyboard,
    )
    await callback.answer("Сервер удалён")


@router.callback_query(F.data.startswith("server:"))
async def server_action_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    _, action, server_id_raw = callback.data.split(":")
    server_id = int(server_id_raw)

    if action == "detail":
        await render_server_detail(callback, server_id)
    elif action == "editprompt":
        detail = await get_server_detail(server_id)
        if not detail:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"✏️ Что изменить у сервера {detail.name}?",
            reply_markup=server_edit_field_keyboard(server_id),
        )
    elif action == "deleteprompt":
        detail = await get_server_detail(server_id)
        if not detail:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"🗑 Удалить сервер {detail.name} и все связанные проверки?",
            reply_markup=server_delete_confirm_keyboard(server_id),
        )
    elif action == "ping":
        text = await run_ping_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "history":
        text = await history_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "ports":
        text = await ports_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "metrics":
        text = await metrics_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "containers":
        text = await containers_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "speed":
        text = await speed_test_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "speedlast":
        text = await latest_speed_test_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
    elif action == "speedhistory":
        text = await speed_test_history_text_by_id(server_id)
        if not text:
            await callback.answer("Сервер не найден", show_alert=True)
            return
        await render_server_action_text(callback, server_id, text)
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
    if not await ensure_callback_allowed(callback):
        return
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
