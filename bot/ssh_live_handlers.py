import asyncio
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.access import ensure_callback_allowed, ensure_message_allowed
from bot.keyboards import server_picker_keyboard
from bot.services import (
    _format_containers_block,
    _format_system_metrics_block,
    find_server_by_id,
    find_server_by_name,
    get_server_detail,
    list_servers_for_picker,
    ssh_monitoring_service,
)


router = Router()


PROGRESS_PLANS = {
    "metrics": [
        (0.0, 8, "Подготовка SSH-сессии"),
        (0.8, 24, "Подключение к VPS"),
        (1.8, 52, "Сбор CPU, RAM, disk и network"),
        (3.0, 82, "Сохранение снимка метрик"),
        (4.2, 95, "Формирую итоговый ответ"),
    ],
    "containers": [
        (0.0, 8, "Подготовка SSH-сессии"),
        (0.8, 26, "Подключение к VPS"),
        (1.8, 58, "Читаю Docker-контейнеры"),
        (3.0, 84, "Сохраняю снимок контейнеров"),
        (4.2, 95, "Формирую итоговый ответ"),
    ],
}


def _progress_bar(percent: int, width: int = 10) -> str:
    clamped = max(0, min(int(percent), 100))
    filled = round((clamped / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _progress_snapshot(view: str, elapsed_seconds: float) -> tuple[int, str]:
    current_percent = 0
    current_stage = "Ожидание"
    for threshold, percent, stage in PROGRESS_PLANS[view]:
        if elapsed_seconds >= threshold:
            current_percent = percent
            current_stage = stage
    return current_percent, current_stage


def _progress_text(server_name: str, view: str, percent: int, stage: str) -> str:
    title = "🧠 Сбор SSH-метрик" if view == "metrics" else "🐳 Сбор Docker-контейнеров"
    return (
        f"{title} для {server_name}\n\n"
        f"Этап: {stage}\n"
        f"Прогресс: [{_progress_bar(percent)}] {percent}%\n\n"
        "Сообщение обновляется автоматически."
    )


def _final_text(detail, view: str) -> str:
    if view == "metrics":
        return _format_system_metrics_block(detail)
    return _format_containers_block(detail)


async def _send_picker(message: Message, action: str, title: str) -> None:
    servers = await list_servers_for_picker()
    if not servers:
        await message.answer(
            "📭 Пока нет добавленных серверов. Сначала добавь сервер через /addserver или из панели."
        )
        return
    await message.answer(title, reply_markup=server_picker_keyboard(servers, action))


async def _track_live_collection(message: Message, *, server, view: str) -> None:
    collection_task = asyncio.create_task(ssh_monitoring_service.collect_server_metrics(server.id))
    started = time.monotonic()
    last_text = None

    while not collection_task.done():
        percent, stage = _progress_snapshot(view, time.monotonic() - started)
        text = _progress_text(server.name, view, percent, stage)
        if text != last_text:
            try:
                await message.edit_text(text)
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    break
            last_text = text
        await asyncio.sleep(1)

    try:
        await collection_task
    except Exception as exc:
        prefix = "SSH-метрики" if view == "metrics" else "Docker-контейнеры"
        await message.edit_text(f"❌ Не удалось получить {prefix.lower()} для {server.name}: {exc}")
        return

    detail = await get_server_detail(server.id)
    if not detail:
        await message.edit_text("❌ Сервер не найден после завершения сбора.")
        return

    await message.edit_text(_final_text(detail, view))


async def _start_live_collection(
    message: Message,
    *,
    view: str,
    server_id: int | None = None,
    server_name: str | None = None,
) -> None:
    server = await (find_server_by_id(server_id) if server_id is not None else find_server_by_name(server_name or ""))
    if not server:
        await message.answer("❌ Сервер не найден.")
        return
    if not server.ssh_enabled:
        await message.answer(
            f"⚠️ {server.name}\n\nSSH сейчас отключён. Открой сервер в панели и заполни SSH-настройки."
        )
        return

    initial_title = "🧠 Запускаю сбор SSH-метрик" if view == "metrics" else "🐳 Запускаю сбор контейнеров"
    progress_message = await message.answer(
        _progress_text(server.name, view, 0, initial_title),
    )
    asyncio.create_task(_track_live_collection(progress_message, server=server, view=view))


@router.message(Command("metrics"))
async def cmd_metrics_live(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        await _start_live_collection(message, view="metrics", server_name=command.args.strip())
        return
    await _send_picker(message, "metrics", "🧠 Выбери сервер для SSH-метрик")


@router.message(Command("containers"))
async def cmd_containers_live(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        await _start_live_collection(message, view="containers", server_name=command.args.strip())
        return
    await _send_picker(message, "containers", "🐳 Выбери сервер для Docker-контейнеров")


@router.callback_query(F.data.startswith("server:metrics:"))
async def server_metrics_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    try:
        _, _, server_id_raw = callback.data.split(":")
        server_id = int(server_id_raw)
    except (AttributeError, ValueError):
        await callback.answer("Не удалось прочитать сервер", show_alert=True)
        return
    await callback.answer("Собираю SSH-метрики")
    await _start_live_collection(callback.message, view="metrics", server_id=server_id)


@router.callback_query(F.data.startswith("server:containers:"))
async def server_containers_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return
    try:
        _, _, server_id_raw = callback.data.split(":")
        server_id = int(server_id_raw)
    except (AttributeError, ValueError):
        await callback.answer("Не удалось прочитать сервер", show_alert=True)
        return
    await callback.answer("Собираю Docker-контейнеры")
    await _start_live_collection(callback.message, view="containers", server_id=server_id)
