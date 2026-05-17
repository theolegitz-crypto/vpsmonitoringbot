import logging

import httpx

from backend.app.core.config import settings


logger = logging.getLogger(__name__)


class TelegramNotifier:
    async def send(self, message: str) -> bool:
        if not settings.telegram_bot_token or not settings.admin_chat_ids:
            return False

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        success = False

        async with httpx.AsyncClient(timeout=10.0) as client:
            for chat_id in settings.admin_chat_ids:
                try:
                    response = await client.post(url, json={"chat_id": chat_id, "text": message})
                    response.raise_for_status()
                    success = True
                except httpx.HTTPError as exc:
                    logger.warning("Failed to send Telegram alert to %s: %s", chat_id, exc)

        return success

