import asyncio
import json

from sqlalchemy import func, select

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models import Server, SpeedTestResult, SpeedTestStatus
from backend.app.services.speedtests import SpeedTestService


speed_test_service = SpeedTestService(AsyncSessionLocal)


STAGE_TITLES = {
    "Queued": "В очереди",
    "Waiting for SSH connection": "Ожидание SSH-подключения",
    "Preparing SSH speed test": "Подготовка speed test",
    "Connecting to the VPS": "Подключение к VPS",
    "Starting remote command": "Запуск удалённой команды",
    "Testing latency": "Проверка задержки",
    "Measuring download": "Измерение download",
    "Measuring upload": "Измерение upload",
    "Completed": "Завершено",
    "Failed": "Ошибка",
    "Cancelling": "Отмена",
    "Cancelled": "Отменено",
}


def _normalize_speed_test_error(value) -> str:
    if not value:
        return "unknown error"
    if isinstance(value, dict):
        return value.get("error") or json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return text
            if isinstance(payload, dict):
                return payload.get("error") or json.dumps(payload, ensure_ascii=False)
        return text
    return str(value)


def _safe_speed(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} Mbps"


def _safe_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} ms"


def _progress_bar(percent: int, width: int = 10) -> str:
    clamped = max(0, min(int(percent), 100))
    filled = round((clamped / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _stage_title(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return "Ожидание"
    return STAGE_TITLES.get(normalized, normalized)


def _progress_percent(speed_test: SpeedTestResult) -> int:
    details = speed_test.details or {}
    raw = details.get("progress_percent", 0)
    try:
        return max(0, min(int(raw), 100))
    except (TypeError, ValueError):
        return 0


def _progress_stage(speed_test: SpeedTestResult) -> str:
    details = speed_test.details or {}
    return _stage_title(details.get("progress_stage"))


def _ssh_debug_block(server: Server) -> str:
    host = (server.ssh_host or server.address or "").strip() or "not set"
    username = (server.ssh_username or "").strip() or "not set"
    password_state = "saved" if server.ssh_password_configured else "not saved"
    enabled_state = "on" if server.ssh_enabled else "off"
    return (
        f"SSH toggle: {enabled_state}\n"
        f"SSH host: {host}\n"
        f"SSH user: {username}\n"
        f"SSH password: {password_state}"
    )


def _active_speed_test_text(
    server_name: str,
    speed_test: SpeedTestResult,
    *,
    intro: str | None = None,
) -> str:
    percent = _progress_percent(speed_test)
    stage = _progress_stage(speed_test)
    status_title = "В очереди" if speed_test.status == SpeedTestStatus.PENDING else "Выполняется"
    lines = [f"⚡ Speed test для {server_name}"]
    if intro:
        lines.extend(["", intro])
    lines.extend(
        [
            "",
            f"Статус: {status_title}",
            f"Этап: {stage}",
            f"Прогресс: [{_progress_bar(percent)}] {percent}%",
            "",
            "Сообщение обновляется автоматически.",
        ]
    )
    return "\n".join(lines)


def _completed_speed_test_text(server_name: str, speed_test: SpeedTestResult) -> str:
    if speed_test.status == SpeedTestStatus.CANCELLED:
        return (
            f"⚡ Speed test для {server_name}\n\n"
            "Статус: Отменён\n"
            f"Комментарий: {_normalize_speed_test_error(speed_test.error) or 'Cancelled by user'}"
        )

    if speed_test.status == SpeedTestStatus.FAILED:
        return (
            f"⚡ Speed test для {server_name}\n\n"
            "Статус: Ошибка\n"
            f"Ошибка: {_normalize_speed_test_error(speed_test.error)}"
        )

    return (
        f"⚡ Speed test для {server_name}\n\n"
        "Статус: Завершено\n"
        f"Провайдер: {speed_test.provider_name or 'n/a'}\n"
        f"Локация: {speed_test.provider_location or 'n/a'}\n"
        f"IP: {speed_test.external_ip or 'n/a'}\n"
        f"Download: {_safe_speed(speed_test.download_mbps)}\n"
        f"Upload: {_safe_speed(speed_test.upload_mbps)}\n"
        f"Ping: {_safe_latency(speed_test.ping_ms)}\n"
        f"Jitter: {_safe_latency(speed_test.jitter_ms)}\n"
        f"Завершён: {speed_test.completed_at.isoformat() if speed_test.completed_at else 'n/a'}"
    )


def _render_speed_test_text(
    server_name: str,
    speed_test: SpeedTestResult,
    *,
    intro: str | None = None,
) -> tuple[str, bool]:
    if speed_test.status in {SpeedTestStatus.PENDING, SpeedTestStatus.RUNNING}:
        return _active_speed_test_text(server_name, speed_test, intro=intro), False
    return _completed_speed_test_text(server_name, speed_test), True


async def _find_server_by_name(name: str) -> Server | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))


def tracking_window_seconds() -> int:
    return (
        settings.ssh_speed_test_timeout_seconds
        + settings.ssh_connect_timeout_seconds
        + settings.scheduler_tick_seconds
        + 60
    )


async def queue_speed_test_for_bot(server_id: int) -> tuple[str | None, int | None, bool]:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)

    if not server:
        return None, None, False

    if not server.ssh_enabled or not server.ssh_username or not server.ssh_password_configured:
        problems = []
        if not server.ssh_enabled:
            problems.append("SSH disabled")
        if not server.ssh_username:
            problems.append("SSH username missing")
        if not server.ssh_password_configured:
            problems.append("SSH password missing")
        text = (
            f"⚡ {server.name}\n\n"
            "Speed test по SSH сейчас недоступен.\n"
            f"Причина: {', '.join(problems)}\n\n"
            f"{_ssh_debug_block(server)}\n\n"
            "Открой сервер в панели, сохрани SSH-настройки и попробуй ещё раз."
        )
        return text, None, False

    speed_test, queued = await speed_test_service.queue_speed_test(server.id)
    asyncio.create_task(speed_test_service.process_queued_ssh_speed_tests())

    intro = (
        "Задача поставлена в очередь. Сразу начинаю SSH-проверку."
        if queued
        else "У сервера уже есть активный speed test. Показываю его текущий прогресс."
    )
    text, done = _render_speed_test_text(server.name, speed_test, intro=intro)
    return text, speed_test.id, not done


async def queue_speed_test_for_bot_by_name(name: str) -> tuple[str | None, int | None, bool]:
    server = await _find_server_by_name(name)
    if not server:
        return None, None, False
    return await queue_speed_test_for_bot(server.id)


async def speed_test_progress_text_by_id(speed_test_id: int) -> tuple[str, bool]:
    async with AsyncSessionLocal() as session:
        speed_test = await session.get(SpeedTestResult, speed_test_id)
        if not speed_test:
            return "❌ Speed test не найден.", True
        server = await session.get(Server, speed_test.server_id)

    server_name = server.name if server else "сервер"
    return _render_speed_test_text(server_name, speed_test)


async def cancel_speed_test_for_bot(speed_test_id: int) -> str:
    cancelled, reason = await speed_test_service.cancel_speed_test(speed_test_id)
    if cancelled and reason == "queued":
        return "⛔ Speed test снят из очереди."
    if cancelled and reason == "running":
        return "⛔ Отправил запрос на остановку speed test. Жду завершения отмены."
    if reason == "already_cancelled":
        return "⛔ Этот speed test уже отменён."
    if reason == "completed":
        return "⚠️ Speed test уже завершён."
    if reason == "failed":
        return "⚠️ Speed test уже завершился ошибкой."
    return "❌ Не удалось остановить speed test."
