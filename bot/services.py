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


async def find_server_by_name(name: str) -> Server | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(Server).where(func.lower(Server.name) == name.lower()))


async def find_service_check_by_name(name: str) -> ServiceCheck | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(ServiceCheck).where(func.lower(ServiceCheck.name) == name.lower()))


async def status_summary_text() -> str:
    overview = await dashboard_service.build_overview()
    return (
        f"Total: {overview.summary.total}\n"
        f"UP: {overview.summary.online}\n"
        f"WARN: {overview.summary.degraded}\n"
        f"DOWN: {overview.summary.offline}\n"
        f"NODATA: {overview.summary.unknown}"
    )


async def servers_text() -> str:
    servers = await dashboard_service.list_servers()
    if not servers:
        return "No servers configured yet."
    return "\n".join(
        f"{STATUS_LABELS[item.status]:<6} {item.name} ({item.address}) latency={item.last_latency_ms or 0:.1f}ms loss={item.last_packet_loss or 0:.1f}%"
        for item in servers
    )


async def server_detail_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    detail = await dashboard_service.build_server_detail(server.id)
    if not detail:
        return None

    checks = "\n".join(
        f"- {check.name}: {STATUS_LABELS[check.status]} target={check.target}"
        for check in detail.services
    ) or "- no service checks"

    return (
        f"{detail.name} ({detail.address})\n"
        f"Status: {STATUS_LABELS[detail.status]}\n"
        f"Latency: {detail.last_latency_ms or 0:.1f} ms\n"
        f"Packet loss: {detail.last_packet_loss or 0:.1f}%\n"
        f"Jitter: {detail.last_jitter_ms or 0:.1f} ms\n"
        f"Muted until: {detail.muted_until.isoformat() if detail.muted_until else 'no'}\n"
        f"Uptime 24h/7d/30d: {detail.uptime_24h:.1f}% / {detail.uptime_7d:.1f}% / {detail.uptime_30d:.1f}%\n"
        f"Checks:\n{checks}"
    )


async def alerts_text() -> str:
    async with AsyncSessionLocal() as session:
        events = (
            await session.scalars(select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(10))
        ).all()
    if not events:
        return "No alert events yet."
    return "\n".join(
        f"[{event.created_at:%Y-%m-%d %H:%M}] {event.event_type.upper()} {event.message}"
        for event in events
    )


async def history_text(name: str) -> str | None:
    server = await find_server_by_name(name)
    if not server:
        return None

    history = await dashboard_service.list_server_history(server.id, limit=32)
    if not history:
        return f"{server.name}: no checks yet."

    strip = "".join(HISTORY_SYMBOLS[item.status] for item in history)
    return f"{server.name}: {strip}\nLegend: G=up Y=warn R=down N=no-data"


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
        f"{refreshed.name}: {STATUS_LABELS[refreshed.status]}\n"
        f"Latency: {refreshed.last_latency_ms or 0:.1f} ms\n"
        f"Packet loss: {refreshed.last_packet_loss or 0:.1f}%\n"
        f"Jitter: {refreshed.last_jitter_ms or 0:.1f} ms"
    )


async def run_ssl_text(domain: str) -> str:
    result = await check_ssl_expiry(domain, 443, settings.http_timeout_seconds, settings.ssl_warning_days)
    return (
        f"SSL {domain}: {STATUS_LABELS[result.status]}\n"
        f"{result.message}"
    )

