import logging

import httpx

from backend.app.core.config import settings


logger = logging.getLogger(__name__)


class TelegramNotifier:
    async def send(self, message: str) -> bool:
        if not settings.telegram_bot_token or not settings.admin_chat_targets:
            if settings.telegram_bot_token and not settings.admin_chat_targets:
                logger.warning(
                    "Telegram alerts are enabled, but no valid targets were parsed from TELEGRAM_ADMIN_CHAT_IDS=%r",
                    settings.telegram_admin_chat_ids,
                )
            return False

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        success = False

        async with httpx.AsyncClient(timeout=10.0) as client:
            for target in settings.admin_chat_targets:
                payload = {"chat_id": target.chat_id, "text": message}
                if target.message_thread_id is not None:
                    payload["message_thread_id"] = target.message_thread_id
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    success = True
                except httpx.HTTPStatusError as exc:
                    body = ""
                    try:
                        body = exc.response.text
                    except Exception:
                        body = "<unavailable>"
                    logger.warning(
                        "Telegram API rejected alert for chat=%s topic=%s status=%s body=%s",
                        target.chat_id,
                        target.message_thread_id,
                        exc.response.status_code if exc.response else "n/a",
                        body,
                    )
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Failed to send Telegram alert to chat=%s topic=%s: %s",
                        target.chat_id,
                        target.message_thread_id,
                        exc,
                    )

        return success
