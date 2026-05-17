from datetime import datetime, timezone

from sqlalchemy import func, select

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models import AlertEvent, CheckType, Server, ServerStatus, ServiceCheck
from backend.app.services.dashboard import DashboardService
from backend.app.services.monitoring import MonitoringService
from backend.app.services.server_management import apply_server_updates
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

SERVER_EDIT_FIELD_META = {
    "name": {
        "label": "имя",
        "prompt": "Введи новое имя сервера.",
        "type": "text",
    },
    "address": {
        "label": "адрес",
        "prompt": "Введи новый IP или домен сервера.",
        "type": "text",
    },
    "description": {
        "label": "описание",
        "prompt": "Введи новое описание или отправь `-`, чтобы очистить поле.",
        "type": "optional_text",
    },
    "check_interval_seconds": {
        "label": "интервал проверки",
        "prompt": "Введи новый интервал проверки в секундах, например `60`.",
        "type": "int",
        "min": 10,
    },
    "consecutive_alert_threshold": {
        "label": "порог подряд идущих ошибок",
        "prompt": "Введи число неудачных проверок подряд перед алертом, например `3`.",
        "type": "int",
        "min": 1,
    },
    "latency_warning_ms": {
        "label": "latency warning",
        "prompt": "Введи warning-порог задержки в миллисекундах, например `150`.",
        "type": "float",
        "min": 1,
    },
    "latency_critical_ms": {
        "label": "latency critical",
        "prompt": "Введи critical-порог задержки в миллисекундах, например `400`.",
        "type": "float",
        "min": 1,
    },
    "packet_loss_warning": {
        "label": "packet loss warning",
        "prompt": "Введи warning-порог потерь пакетов в процентах, например `5`.",
        "type": "percent",
    },
    "packet_loss_critical": {
        "label": "packet loss critical",
        "prompt": "Введи critical-порог потерь пакетов в процентах, например `20`.",
        "type": "percent",
    },
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


def normalize_optional_text(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"-", "нет", "none", "skip", "пропустить"}:
        return None
    return cleaned


def parse_ports_input(value: str) -> list[int]:
    normalized = normalize_optional_text(value)
    if not normalized:
        return []

    ports: list[int] = []
    for raw in normalized.split(","):
        item = raw.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError("Порты нужно указывать числами через запятую, например: 22,80,443")
        port = int(item)
        if port < 1 or port > 65535:
            raise ValueError("Порт должен быть в диапазоне 1-65535")
        ports.append(port)
    return ports


def help_text() -> str:
    return (
        "🤖 Команды SwagMonitor\n\n"
        "/status - общий статус всех мониторов\n"
        "/servers - список серверов с выбором кнопками\n"
        "/server - выбрать сервер и открыть подробности\n"
        "/ping - выбрать сервер и запустить ping\n"
        "/history - выбрать сервер и открыть историю\n"
        "/ports - выбрать сервер и посмотреть TCP, HTTP и SSL\n"
        "/alerts - последние события и алерты\n"
        "/addserver - добавить сервер прямо через Telegram\n"
        "/mute - приглушить уведомления для сервера\n"
        "/unmute - снова включить уведомления\n"
        "/chatinfo - показать chat id и topic id\n"
        "/ssl <domain> - вручную проверить сертификат\n\n"
        "🧭 Как пользоваться\n"
        "1. Добавь сервер через веб-панель или /addserver.\n"
        "2. Открой /servers или нажми кнопку «Серверы».\n"
        "3. Выбирай нужный сервер кнопками, без ручного ввода имени.\n"
        "4. В карточке сервера доступны ping, история, порты, редактирование и удаление.\n\n"
        "История: 🟩 OK  🟨 деградация  🟥 сбой  ⬜ нет данных"
    )


def get_server_edit_field_meta(field: str) -> dict:
    meta = SERVER_EDIT_FIELD_META.get(field)
    if not meta:
        raise ValueError("Неизвестное поле для редактирования")
    return meta


def _parse_server_field_value(field: str, raw_value: str):
    meta = get_server_edit_field_meta(field)
    value = raw_value.strip()

    if meta["type"] == "text":
        if len(value) < 2:
            raise ValueError("Значение слишком короткое.")
        return value

    if meta["type"] == "optional_text":
        return normalize_optional_text(value)

    if meta["type"] == "int":
        if not value.isdigit():
            raise ValueError("Нужно ввести целое число.")
        parsed = int(value)
        if parsed < meta["min"]:
            raise ValueError(f"Значение должно быть не меньше {meta['min']}.")
        return parsed

    normalized = value.replace(",", ".")
    try:
        parsed = float(normalized)
    except ValueError as exc:
        raise ValueError("Нужно ввести число.") from exc

    if meta["type"] == "percent":
        if parsed < 0 or parsed > 100:
            raise ValueError("Процент должен быть в диапазоне 0-100.")
        return parsed

    if parsed < meta["min"]:
        raise ValueError(f"Значение должно быть не меньше {meta['min']}.")
    return parsed


async def list_servers_for_picker():
    return await dashboard_service.list_servers()


async def create_server_from_bot(
    *,
    name: str,
    address: str,
    description: str | None,
    website_url: str | None,
    tcp_ports: list[int],
    ssl_domain: str | None,
) -> tuple[Server, int]:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))
        if existing:
            raise ValueError("Сервер с таким именем уже существует")

        server = Server(
            name=name,
            address=address,
            description=description,
            check_interval_seconds=settings.default_check_interval_seconds,
            consecutive_alert_threshold=settings.default_consecutive_alert_threshold,
        )
        session.add(server)
        await session.flush()

        checks_added = 0

        if website_url:
            session.add(
                ServiceCheck(
                    server_id=server.id,
                    name=f"{name}-http",
                    check_type=CheckType.HTTP,
                    target=website_url,
                    path="",
                    timeout_seconds=settings.http_timeout_seconds,
                    interval_seconds=settings.default_check_interval_seconds,
                    expected_status=200,
                    ssl_expiry_warning_days=settings.ssl_warning_days,
                    consecutive_alert_threshold=settings.default_consecutive_alert_threshold,
                )
            )
            checks_added += 1

        for port in tcp_ports:
            session.add(
                ServiceCheck(
                    server_id=server.id,
                    name=f"{name}-tcp-{port}",
                    check_type=CheckType.TCP,
                    target=address,
                    port=port,
                    timeout_seconds=settings.http_timeout_seconds,
                    interval_seconds=settings.default_check_interval_seconds,
                    expected_status=200,
                    ssl_expiry_warning_days=settings.ssl_warning_days,
                    consecutive_alert_threshold=settings.default_consecutive_alert_threshold,
                )
            )
            checks_added += 1

        if ssl_domain:
            session.add(
                ServiceCheck(
                    server_id=server.id,
                    name=f"{name}-ssl",
                    check_type=CheckType.SSL,
                    target=ssl_domain,
                    port=443,
                    timeout_seconds=settings.http_timeout_seconds,
                    interval_seconds=max(3600, settings.default_check_interval_seconds),
                    expected_status=200,
                    ssl_expiry_warning_days=settings.ssl_warning_days,
                    consecutive_alert_threshold=settings.default_consecutive_alert_threshold,
                )
            )
            checks_added += 1

        await session.commit()
        await session.refresh(server)
        return server, checks_added


async def find_server_by_name(name: str) -> Server | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))


async def find_server_by_id(server_id: int) -> Server | None:
    async with AsyncSessionLocal() as session:
        return await session.get(Server, server_id)


async def get_server_detail(server_id: int):
    return await dashboard_service.build_server_detail(server_id)


async def status_summary_text() -> str:
    overview = await dashboard_service.build_overview()
    if not overview.servers:
        return (
            "📭 Пока нет добавленных мониторов.\n\n"
            "Открой веб-панель или используй /addserver, чтобы создать первый VPS."
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
        "Открой «🖥 Серверы» и выбери нужный сервер кнопкой."
    )


async def servers_text() -> str:
    servers = await dashboard_service.list_servers()
    if not servers:
        return "📭 Пока нет добавленных серверов. Добавь первый через веб-панель или /addserver."
    return (
        "🖥 Список серверов готов.\n"
        "Нажми на нужный сервер в кнопках ниже, чтобы открыть детали."
    )


async def server_detail_text_by_id(server_id: int) -> str | None:
    detail = await get_server_detail(server_id)
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


async def server_detail_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None
    return await server_detail_text_by_id(server.id)


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


async def history_text_by_id(server_id: int) -> str | None:
    server = await find_server_by_id(server_id)
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


async def history_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None
    return await history_text_by_id(server.id)


async def ports_text_by_id(server_id: int) -> str | None:
    detail = await get_server_detail(server_id)
    if not detail:
        return None

    relevant = [check for check in detail.services if check.check_type.value in {"tcp", "http", "ssl"}]
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


async def ports_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None
    return await ports_text_by_id(server.id)


async def mute_text_by_id(server_id: int, duration: str) -> str | None:
    until = datetime.now(timezone.utc) + parse_duration(duration)

    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            return None
        server.muted_until = until
        await session.commit()
        return f"🔕 Сервер {server.name}: уведомления выключены до {until.isoformat()}"


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


async def unmute_text_by_id(server_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            return None
        server.muted_until = None
        await session.commit()
        return f"🔔 Сервер {server.name}: уведомления снова включены"


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


async def run_ping_text_by_id(server_id: int) -> str | None:
    server = await find_server_by_id(server_id)
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


async def run_ping_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None
    return await run_ping_text_by_id(server.id)


async def run_ssl_text(domain: str) -> str:
    result = await check_ssl_expiry(domain, 443, settings.http_timeout_seconds, settings.ssl_warning_days)
    return (
        f"🔐 SSL {domain}\n"
        f"Статус: {_status_text(result.status)}\n"
        f"{result.message}"
    )


async def update_server_field_by_id(server_id: int, field: str, raw_value: str) -> Server | None:
    parsed_value = _parse_server_field_value(field, raw_value)

    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            return None

        await apply_server_updates(session, server, {field: parsed_value})
        await session.commit()
        await session.refresh(server)
        return server


async def delete_server_by_id(server_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            return None

        name = server.name
        await session.delete(server)
        await session.commit()
        return name
