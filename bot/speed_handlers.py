import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.access import ensure_callback_allowed, ensure_message_allowed
from bot.keyboards import server_picker_keyboard
from bot.speed_live import (
    cancel_speed_test_for_bot,
    queue_speed_test_for_bot,
    queue_speed_test_for_bot_by_name,
    speed_test_progress_text_by_id,
    tracking_window_seconds,
)
from bot.services import list_servers_for_picker


router = Router()


def _speed_progress_keyboard(speed_test_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛔ Остановить speed test", callback_data=f"speedstop:{speed_test_id}")]
        ]
    )


async def _send_speed_picker(message: Message) -> None:
    servers = await list_servers_for_picker()
    if not servers:
        await message.answer(
            "📭 Пока нет добавленных серверов. Сначала добавь сервер через /addserver или из панели.",
        )
        return
    await message.answer(
        "⚡ Выбери сервер для speed test",
        reply_markup=server_picker_keyboard(servers, "speed"),
    )


async def _track_speed_test_message(message: Message, speed_test_id: int) -> None:
    last_text = None
    attempts = max(40, tracking_window_seconds() // 3)
    for _ in range(attempts):
        text, done = await speed_test_progress_text_by_id(speed_test_id)
        if text != last_text:
            try:
                await message.edit_text(
                    text,
                    reply_markup=None if done else _speed_progress_keyboard(speed_test_id),
                )
            except TelegramBadRequest as exc:
                error_text = str(exc).lower()
                if "message is not modified" not in error_text:
                    break
            last_text = text
        if done:
            break
        await asyncio.sleep(3)


async def _start_speed_flow(
    message: Message,
    *,
    server_id: int | None = None,
    server_name: str | None = None,
) -> None:
    if server_id is not None:
        text, speed_test_id, should_track = await queue_speed_test_for_bot(server_id)
    else:
        text, speed_test_id, should_track = await queue_speed_test_for_bot_by_name(server_name or "")

    if not text:
        await message.answer("❌ Сервер не найден.")
        return

    progress_message = await message.answer(
        text,
        reply_markup=_speed_progress_keyboard(speed_test_id) if speed_test_id and should_track else None,
    )
    if speed_test_id and should_track:
        asyncio.create_task(_track_speed_test_message(progress_message, speed_test_id))


@router.message(Command("speed"))
async def cmd_speed_live(message: Message, command: CommandObject) -> None:
    if not await ensure_message_allowed(message):
        return
    if command.args:
        await _start_speed_flow(message, server_name=command.args.strip())
        return
    await _send_speed_picker(message)


@router.callback_query(F.data.startswith("server:speed:"))
async def server_speed_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return

    try:
        _, _, server_id_raw = callback.data.split(":")
        server_id = int(server_id_raw)
    except (AttributeError, ValueError):
        await callback.answer("Не удалось прочитать сервер", show_alert=True)
        return

    await callback.answer("Запускаю speed test")
    await _start_speed_flow(callback.message, server_id=server_id)


@router.callback_query(F.data.startswith("speedstop:"))
async def speed_stop_callback(callback: CallbackQuery) -> None:
    if not await ensure_callback_allowed(callback):
        return

    try:
        _, speed_test_id_raw = callback.data.split(":")
        speed_test_id = int(speed_test_id_raw)
    except (AttributeError, ValueError):
        await callback.answer("Не удалось прочитать speed test", show_alert=True)
        return

    status_text = await cancel_speed_test_for_bot(speed_test_id)
    await callback.answer(status_text)

    text, done = await speed_test_progress_text_by_id(speed_test_id)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=None if done else _speed_progress_keyboard(speed_test_id),
        )
    except TelegramBadRequest:
        pass
