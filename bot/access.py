from aiogram.types import CallbackQuery, Message

from backend.app.core.config import settings


def describe_telegram_context(
    *,
    chat_id: int,
    chat_type: str,
    message_thread_id: int | None,
) -> str:
    binding = format_telegram_target(chat_id=chat_id, message_thread_id=message_thread_id)
    topic_line = (
        f"Topic ID: `{message_thread_id}`\n"
        if message_thread_id is not None
        else "Topic ID: `none`\n"
    )
    return (
        "📌 Информация о текущем чате\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Тип чата: `{chat_type}`\n"
        f"{topic_line}"
        f"Готовое значение для .env: `{binding}`\n\n"
        "Используй это значение в `TELEGRAM_ADMIN_CHAT_IDS` для алертов\n"
        "или в `TELEGRAM_ALLOWED_CHAT_IDS`, чтобы разрешить работу бота только здесь."
    )


def format_telegram_target(*, chat_id: int, message_thread_id: int | None) -> str:
    if message_thread_id is None:
        return str(chat_id)
    return f"{chat_id}:{message_thread_id}"


def is_message_allowed(message: Message) -> bool:
    return settings.is_allowed_telegram_context(
        chat_id=message.chat.id,
        message_thread_id=getattr(message, "message_thread_id", None),
        chat_type=message.chat.type,
    )


def is_callback_allowed(callback: CallbackQuery) -> bool:
    message = callback.message
    if message is None:
        return True
    return settings.is_allowed_telegram_context(
        chat_id=message.chat.id,
        message_thread_id=getattr(message, "message_thread_id", None),
        chat_type=message.chat.type,
    )


async def ensure_message_allowed(message: Message) -> bool:
    return is_message_allowed(message)


async def ensure_callback_allowed(callback: CallbackQuery) -> bool:
    if is_callback_allowed(callback):
        return True
    await callback.answer("Эта группа или тема не разрешена для работы бота.", show_alert=True)
    return False
