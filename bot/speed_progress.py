from backend.app.db.session import AsyncSessionLocal
from backend.app.models import Server, SpeedTestResult, SpeedTestStatus
from backend.app.services.speedtests import SpeedTestService


speed_test_service = SpeedTestService(AsyncSessionLocal)


def _safe_speed(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} Mbps"


def _safe_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} ms"


def _progress_bar(percent: int, width: int = 10) -> str:
    safe_percent = max(0, min(int(percent), 100))
    filled = round((safe_percent / 100) * width)
    return "🟩" * filled + "⬜" * max(width - filled, 0)


def _normalize_error(value) -> str:
    if not value:
        return "unknown error"
    if isinstance(value, dict):
        return str(value.get("error") or value)
    text = str(value).strip()
    if text.startswith("{") and text.endswith("}") and "\"error\"" in text:
        text = text.replace("{", "").replace("}", "").replace("\"", "")
        if ":" in text:
            text = text.split(":", 1)[1].strip()
    return text


def _completed_block(server_name: str, speed_test: SpeedTestResult) -> str:
    if speed_test.status == SpeedTestStatus.FAILED:
        return (
            f"❌ {server_name}\n"
            "Последний speed test завершился ошибкой.\n"
            f"Ошибка: {_normalize_error(speed_test.error)}"
        )

    return (
        f"✅ {server_name}\n"
        "Последний speed test\n"
        f"Провайдер: {speed_test.provider_name or 'n/a'}\n"
        f"Локация: {speed_test.provider_location or 'n/a'}\n"
        f"IP: {speed_test.external_ip or 'n/a'}\n"
        f"Download: {_safe_speed(speed_test.download_mbps)}\n"
        f"Upload: {_safe_speed(speed_test.upload_mbps)}\n"
        f"Ping: {_safe_latency(speed_test.ping_ms)}\n"
        f"Завершён: {speed_test.completed_at.isoformat() if speed_test.completed_at else 'n/a'}"
    )


async def queue_speed_test_for_bot(server_id: int) -> tuple[str | None, int | None, bool]:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            return None, None, False
        if not server.ssh_enabled:
            return (
                f"⚡ {server.name}\n"
                "Speed test по SSH пока недоступен.\n"
                "Открой сервер в панели, включи SSH и заполни логин с паролем.",
                None,
                False,
            )

    speed_test, queued = await speed_test_service.queue_speed_test(server_id)
    if queued:
        return (
            "⚡ Speed test поставлен в очередь.\n"
            "Сейчас начну обновлять прогресс в этом сообщении.",
            speed_test.id,
            True,
        )

    return (
        "⚡ Уже есть незавершённый speed test.\n"
        "Подключаюсь к его текущему прогрессу.",
        speed_test.id,
        True,
    )


async def speed_test_progress_text_by_id(speed_test_id: int) -> tuple[str, bool]:
    async with AsyncSessionLocal() as session:
        item = await session.get(SpeedTestResult, speed_test_id)
        if not item:
            return "❌ Задача speed test не найдена.", True

        server = await session.get(Server, item.server_id)
        server_name = server.name if server else f"server #{item.server_id}"
        details = dict(item.details or {})
        progress_percent = int(details.get("progress_percent") or 0)
        progress_stage = str(details.get("progress_stage") or "Queued")

        if item.status in {SpeedTestStatus.COMPLETED, SpeedTestStatus.FAILED}:
            return _completed_block(server_name, item), True

        lines = [
            f"⚡ Speed test для {server_name}",
            f"{_progress_bar(progress_percent)} {progress_percent}%",
            f"Стадия: {progress_stage}",
            f"Статус: {item.status.value.upper()}",
            f"Создан: {item.created_at:%Y-%m-%d %H:%M}",
        ]
        if item.started_at:
            lines.append(f"Стартовал: {item.started_at:%Y-%m-%d %H:%M}")
        return "\n".join(lines), False
