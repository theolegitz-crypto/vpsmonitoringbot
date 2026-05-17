from datetime import datetime, timezone

from sqlalchemy import func, select

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models import AlertEvent, Server, ServerStatus, ServiceCheck
from backend.app.services.dashboard import DashboardService
from backend.app.services.monitoring import MonitoringService
from backend.app.utils.service_checks import check_ssl_expiry
from backend.app.utils.time import parse_duration


dashboard_service = DashboardService(AsyncSessionLocal)
monitoring_service = MonitoringService(AsyncSessionLocal)


STATUS_LABELS = {
    ServerStatus.ONLINE: "🟢 OK",
    ServerStatus.DEGRADED: "🟡 Деградация",
    ServerStatus.OFFLINE: "🔴 Недоступен",
    ServerStatus.UNKNOWN: "⚪ Нет данных",
}

HISTORY_SYMBOLS = {
    ServerStatus.ONLINE: "🟩",
    ServerStatus.DEGRADED: "🟨",
    ServerStatus.OFFLINE: "🟥",
    ServerStatus.UNKNOWN: "⬜",
}


def _format_history_line(history) -> str:
    raw = [HISTORY_SYMBOLS[item.status] for item in history]
    if not raw:
        return "⬜"
    return " ".join("".join(raw[index : index + 8]) for index in range(0, len(raw), 8))


def _status_text(status: ServerStatus) -> str:
    return STATUS_LABELS[status]


def _safe_latency(value: float | None) -> str:
    return f"{(value or 0):.1f} ms"


def _safe_percent(value: float | None) -> str:
    return f"{(value or 0):.1f}%"


def help_text() -> str:
    return (
        "🤖 Команды SwagMonitor\n\n"
        "/status - общий статус всех мониторов\n"
        "/servers - список серверов\n"
        "/server <name> - подробности по одному серверу\n"
        "/ping <name> - запустить ICMP-проверку прямо сейчас\n"
        "/history <name> - последняя история статусов\n"
        "/ports <name> - TCP, HTTP и SSL-проверки сервера\n"
        "/alerts - последние события и алерты\n"
        "/mute <name> <duration> - выключить уведомления, пример: /mute vps1 2h\n"
        "/unmute <name> - снова включить уведомления\n"
        "/ssl <domain> - вручную проверить сертификат\n\n"
        "🧭 Как пользоваться\n"
        "1. Сначала добавь серверы в веб-панели.\n"
        "2. Подожди первые проверки или нажми ручной запуск.\n"
        "3. Используй /status и /server <name> для быстрой диагностики.\n\n"
        "История: 🟩 OK  🟨 деградация  🟥 сбой  ⬜ нет данных"
    )


async def find_server_by_name(name: str) -> Server | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))


async def find_service_check_by_name(name: str) -> ServiceCheck | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower()))


async def status_summary_text() -> str:
    overview = await dashboard_service.build_overview()
    if not overview.servers:
        return (
            "📭 Пока нет добавленных мониторов.\n\n"
            "Открой веб-панель и добавь первый VPS:\n"
            "- имя\n"
            "- IP или домен\n"
            "- при желании URL сайта\n"
            "- при желании порты вроде 22, 80, 443\n\n"
            "После этого используй /servers или /server <name>."
        )

    top_rows = "\n".join(
        f"- {_status_text(item.status)} {item.name} | 24ч {item.uptime_24h:.1f}% | потери {_safe_percent(item.last_packet_loss)}"
        for item in overview.servers[:5]
    )
    return (
        "📊 Общий статус\n"
        f"Всего: {overview.summary.total}\n"
        f"🟢 OK: {overview.summary.online}\n"
        f"🟡 Деградация: {overview.summary.degraded}\n"
        f"🔴 Недоступны: {overview.summary.offline}\n"
        f"⚪ Нет данных: {overview.summary.unknown}\n\n"
        "🖥 Кратко по серверам\n"
        f"{top_rows}\n\n"
        "Подробности: /server <name>"
    )


async def servers_text() -> str:
    servers = await dashboard_service.list_servers()
    if not servers:
        return "📭 Пока нет добавленных серверов. Добавь первый через веб-панель."
    lines = ["🖥 Список серверов"]
    for item in servers:
        lines.append(
            f"- {item.name} [{_status_text(item.status)}]\n"
            f"  адрес: {item.address}\n"
            f"  uptime: 24ч {item.uptime_24h:.1f}% | 7д {item.uptime_7d:.1f}% | 30д {item.uptime_30d:.1f}%\n"
            f"  задержка: {_safe_latency(item.last_latency_ms)} | потери: {_safe_percent(item.last_packet_loss)}\n"
            f"  проверок: {len(item.services)}"
        )
    lines.append("\nОткрыть один сервер: /server <name>")
    return "\n".join(lines)


async def server_detail_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    detail = await dashboard_service.build_server_detail(server.id)
    if not detail:
        return None

    checks = "\n".join(
        f"- {check.name} [{_status_text(check.status)}]\n"
        f"  тип: {check.check_type.value} | цель: {check.target}{f':{check.port}' if check.port else ''}\n"
        f"  uptime: 24ч {check.uptime_24h:.1f}% | 7д {check.uptime_7d:.1f}% | 30д {check.uptime_30d:.1f}%\n"
        f"  ответ: {_safe_latency(check.last_response_ms)} | код: {check.last_status_code or 'n/a'}\n"
        f"  история: {_format_history_line(check.history)}"
        for check in detail.services
    ) or "- сервисные проверки пока не добавлены"

    return (
        f"🖥 {detail.name}\n"
        f"Адрес: {detail.address}\n"
        f"Статус: {_status_text(detail.status)}\n"
        f"Uptime: 24ч {detail.uptime_24h:.1f}% | 7д {detail.uptime_7d:.1f}% | 30д {detail.uptime_30d:.1f}%\n"
        f"Ping: средний {_safe_latency(detail.last_latency_ms)} | потери {_safe_percent(detail.last_packet_loss)} | jitter {_safe_latency(detail.last_jitter_ms)}\n"
        f"Уведомления: {'приглушены до ' + detail.muted_until.isoformat() if detail.muted_until else 'активны'}\n"
        f"История: {_format_history_line(detail.history)}\n"
        "Легенда: 🟩 OK  🟨 деградация  🟥 сбой  ⬜ нет данных\n\n"
        f"🔎 Проверки сервисов\n{checks}"
    )


async def alerts_text() -> str:
    async with AsyncSessionLocal() as session:
        events = (
            await session.scalars(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(10))
        ).all()
    if not events:
        return "✅ Пока нет событий алертов. Когда появятся сбои или восстановления, они будут показаны здесь."
    return "🚨 Последние события\n" + "\n".join(
        f"- [{event.created_at:%Y-%m-%d %H:%M}] {event.event_type.upper()} | {event.message}"
        for event in events
    )


async def history_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    history = await dashboard_service.list_server_history(server.id, limit=32)
    if not history:
        return f"📭 {server.name}: пока ещё нет результатов проверок."

    strip = _format_history_line(history)
    return (
        f"🕓 {server.name}\n"
        f"Последняя история: {strip}\n"
        "Легенда: 🟩 OK  🟨 деградация  🟥 сбой  ⬜ нет данных"
    )


async def ports_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    detail = await dashboard_service.build_server_detail(server.id)
    if not detail:
        return None

    relevant = [
        check for check in detail.services if check.check_type.value in {"tcp", "http", "ssl"}
    ]
    if not relevant:
        return f"📭 {detail.name}: пока нет HTTP, TCP или SSL-проверок."

    lines = [f"🔌 Проверки сервисов для {detail.name}"]
    for check in relevant:
        target = check.target
        if check.port:
            target = f"{target}:{check.port}"
        lines.append(
            f"- {check.name} [{_status_text(check.status)}]\n"
            f"  тип: {check.check_type.value} | цель: {target}\n"
            f"  ответ: {_safe_latency(check.last_response_ms)} | код: {check.last_status_code or 'n/a'}"
        )
    return "\n".join(lines)


async def mute_text(name: str, duration: str) -> str | None:
    until = datetime.now(timezone.utc) + parse_duration(duration)

    async with AsyncSessionLocal() as session:
        server = await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))
        if server:
            server.muted_until = until
            await session.commit()
            return f"🔕 Сервер {server.name}: уведомления выключены до {until.isoformat()}"

        service_check = await session.scalar(
            select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower())
        )
        if service_check:
            service_check.muted_until = until
            await session.commit()
            return f"🔕 Проверка {service_check.name}: уведомления выключены до {until.isoformat()}"

    return None


async def unmute_text(name: str) -> str | None:
    async with AsyncSessionLocal() as session:
        server = await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))
        if server:
            server.muted_until = None
            await session.commit()
            return f"🔔 Сервер {server.name}: уведомления снова включены"

        service_check = await session.scalar(
            select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower())
        )
        if service_check:
            service_check.muted_until = None
            await session.commit()
            return f"🔔 Проверка {service_check.name}: уведомления снова включены"

    return None


async def run_ping_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    refreshed = await monitoring_service.run_server_check(server.id)
    if not refreshed:
        return None

    return (
        f"📡 {refreshed.name}\n"
        f"Статус: {_status_text(refreshed.status)}\n"
        f"Задержка: {_safe_latency(refreshed.last_latency_ms)}\n"
        f"Потери: {_safe_percent(refreshed.last_packet_loss)}\n"
        f"Jitter: {_safe_latency(refreshed.last_jitter_ms)}"
    )


async def run_ssl_text(domain: str) -> str:
    result = await check_ssl_expiry(domain, 443, settings.http_timeout_seconds, settings.ssl_warning_days)
    return (
        f"🔐 SSL {domain}\n"
        f"Статус: {_status_text(result.status)}\n"
        f"{result.message}"
    )
