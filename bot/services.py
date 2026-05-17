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
    ServerStatus.ONLINE: "UP",
    ServerStatus.DEGRADED: "WARN",
    ServerStatus.OFFLINE: "DOWN",
    ServerStatus.UNKNOWN: "NODATA",
}

HISTORY_SYMBOLS = {
    ServerStatus.ONLINE: "G",
    ServerStatus.DEGRADED: "Y",
    ServerStatus.OFFLINE: "R",
    ServerStatus.UNKNOWN: "N",
}


def _format_history_line(history) -> str:
    raw = "".join(HISTORY_SYMBOLS[item.status] for item in history)
    if not raw:
        return "NODATA"
    return " ".join(raw[index : index + 8] for index in range(0, len(raw), 8))


def _status_text(status: ServerStatus) -> str:
    return STATUS_LABELS[status]


def _safe_latency(value: float | None) -> str:
    return f"{(value or 0):.1f} ms"


def _safe_percent(value: float | None) -> str:
    return f"{(value or 0):.1f}%"


def help_text() -> str:
    return (
        "SwagMonitor commands\n\n"
        "/status - total state of all monitors\n"
        "/servers - list all servers\n"
        "/server <name> - full details for one server\n"
        "/ping <name> - run ICMP check now\n"
        "/history <name> - show recent status timeline\n"
        "/ports <name> - show TCP/HTTP/SSL checks for server\n"
        "/alerts - last alert events\n"
        "/mute <name> <duration> - mute alerts, example /mute vps1 2h\n"
        "/unmute <name> - enable alerts again\n"
        "/ssl <domain> - check certificate manually\n\n"
        "How to use\n"
        "1. Add servers in the web panel.\n"
        "2. Wait for the first checks.\n"
        "3. Use /status and /server <name> for quick diagnostics.\n\n"
        "Legend for history: G=ok Y=degraded R=down N=no-data"
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
            "No monitors configured yet.\n\n"
            "Open the web panel and add the first VPS:\n"
            "- name\n"
            "- IP or domain\n"
            "- optional website URL\n"
            "- optional ports like 22,80,443\n\n"
            "Then use /servers or /server <name>."
        )

    top_rows = "\n".join(
        f"- {_status_text(item.status):<6} {item.name} | 24h {item.uptime_24h:.1f}% | loss {_safe_percent(item.last_packet_loss)}"
        for item in overview.servers[:5]
    )
    return (
        "Global status\n"
        f"Total: {overview.summary.total}\n"
        f"UP: {overview.summary.online}\n"
        f"WARN: {overview.summary.degraded}\n"
        f"DOWN: {overview.summary.offline}\n"
        f"NODATA: {overview.summary.unknown}\n\n"
        "Top monitors\n"
        f"{top_rows}\n\n"
        "Use /server <name> for details."
    )


async def servers_text() -> str:
    servers = await dashboard_service.list_servers()
    if not servers:
        return "No servers configured yet. Add the first one in the web panel."
    lines = ["Servers"]
    for item in servers:
        lines.append(
            f"- {item.name} [{_status_text(item.status)}]\n"
            f"  target: {item.address}\n"
            f"  uptime: 24h {item.uptime_24h:.1f}% | 7d {item.uptime_7d:.1f}% | 30d {item.uptime_30d:.1f}%\n"
            f"  latency: {_safe_latency(item.last_latency_ms)} | loss: {_safe_percent(item.last_packet_loss)}\n"
            f"  checks: {len(item.services)}"
        )
    lines.append("\nOpen one monitor with /server <name>.")
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
        f"  type: {check.check_type.value} | target: {check.target}{f':{check.port}' if check.port else ''}\n"
        f"  uptime: 24h {check.uptime_24h:.1f}% | 7d {check.uptime_7d:.1f}% | 30d {check.uptime_30d:.1f}%\n"
        f"  response: {_safe_latency(check.last_response_ms)} | status code: {check.last_status_code or 'n/a'}\n"
        f"  history: {_format_history_line(check.history)}"
        for check in detail.services
    ) or "- no service checks"

    return (
        f"{detail.name}\n"
        f"Target: {detail.address}\n"
        f"Status: {_status_text(detail.status)}\n"
        f"Uptime: 24h {detail.uptime_24h:.1f}% | 7d {detail.uptime_7d:.1f}% | 30d {detail.uptime_30d:.1f}%\n"
        f"Ping: avg {_safe_latency(detail.last_latency_ms)} | loss {_safe_percent(detail.last_packet_loss)} | jitter {_safe_latency(detail.last_jitter_ms)}\n"
        f"Muted until: {detail.muted_until.isoformat() if detail.muted_until else 'active'}\n"
        f"History: {_format_history_line(detail.history)}\n"
        "Legend: G=ok Y=degraded R=down N=no-data\n\n"
        f"Service checks\n{checks}"
    )


async def alerts_text() -> str:
    async with AsyncSessionLocal() as session:
        events = (
            await session.scalars(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(10))
        ).all()
    if not events:
        return "No alert events yet. When monitors start failing or recovering, alerts will appear here."
    return "Last alert events\n" + "\n".join(
        f"- [{event.created_at:%Y-%m-%d %H:%M}] {event.event_type.upper()} | {event.message}"
        for event in events
    )


async def history_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    history = await dashboard_service.list_server_history(server.id, limit=32)
    if not history:
        return f"{server.name}: no checks yet."

    strip = _format_history_line(history)
    return (
        f"{server.name}\n"
        f"Recent history: {strip}\n"
        "Legend: G=ok Y=degraded R=down N=no-data"
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
        return f"{detail.name}: no port or web checks configured yet."

    lines = [f"{detail.name} service checks"]
    for check in relevant:
        target = check.target
        if check.port:
            target = f"{target}:{check.port}"
        lines.append(
            f"- {check.name} [{_status_text(check.status)}]\n"
            f"  type: {check.check_type.value} | target: {target}\n"
            f"  response: {_safe_latency(check.last_response_ms)} | code: {check.last_status_code or 'n/a'}"
        )
    return "\n".join(lines)


async def mute_text(name: str, duration: str) -> str | None:
    until = datetime.now(timezone.utc) + parse_duration(duration)

    async with AsyncSessionLocal() as session:
        server = await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))
        if server:
            server.muted_until = until
            await session.commit()
            return f"Server {server.name} muted until {until.isoformat()}"

        service_check = await session.scalar(
            select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower())
        )
        if service_check:
            service_check.muted_until = until
            await session.commit()
            return f"Check {service_check.name} muted until {until.isoformat()}"

    return None


async def unmute_text(name: str) -> str | None:
    async with AsyncSessionLocal() as session:
        server = await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))
        if server:
            server.muted_until = None
            await session.commit()
            return f"Server {server.name} unmuted"

        service_check = await session.scalar(
            select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower())
        )
        if service_check:
            service_check.muted_until = None
            await session.commit()
            return f"Check {service_check.name} unmuted"

    return None


async def run_ping_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    refreshed = await monitoring_service.run_server_check(server.id)
    if not refreshed:
        return None

    return (
        f"{refreshed.name}\n"
        f"Status: {_status_text(refreshed.status)}\n"
        f"Latency: {_safe_latency(refreshed.last_latency_ms)}\n"
        f"Packet loss: {_safe_percent(refreshed.last_packet_loss)}\n"
        f"Jitter: {_safe_latency(refreshed.last_jitter_ms)}"
    )


async def run_ssl_text(domain: str) -> str:
    result = await check_ssl_expiry(domain, 443, settings.http_timeout_seconds, settings.ssl_warning_days)
    return (
        f"SSL {domain}\n"
        f"Status: {_status_text(result.status)}\n"
        f"{result.message}"
    )
