import asyncio
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from urllib.parse import urlparse

import httpx

from backend.app.models.enums import ServerStatus, Severity


@dataclass
class ServiceProbeResult:
    status: ServerStatus
    severity: Severity
    response_time_ms: float | None
    status_code: int | None
    message: str
    details: dict


def _normalize_url(target: str, path: str | None = None) -> str:
    if target.startswith("http://") or target.startswith("https://"):
        base = target.rstrip("/")
    else:
        base = f"https://{target}".rstrip("/")
    return f"{base}{path or ''}"


async def check_http(target: str, path: str | None, expected_status: int, timeout_seconds: int) -> ServiceProbeResult:
    url = _normalize_url(target, path)
    started = perf_counter()

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url)
        duration = (perf_counter() - started) * 1000
        if response.status_code == expected_status or (
            expected_status == 200 and 200 <= response.status_code < 400
        ):
            return ServiceProbeResult(
                status=ServerStatus.ONLINE,
                severity=Severity.INFO,
                response_time_ms=duration,
                status_code=response.status_code,
                message=f"HTTP check passed with {response.status_code}",
                details={"url": url},
            )

        severity = Severity.CRITICAL if response.status_code >= 500 else Severity.WARNING
        return ServiceProbeResult(
            status=ServerStatus.DEGRADED,
            severity=severity,
            response_time_ms=duration,
            status_code=response.status_code,
            message=f"Unexpected HTTP status {response.status_code}",
            details={"url": url},
        )
    except httpx.HTTPError as exc:
        return ServiceProbeResult(
            status=ServerStatus.OFFLINE,
            severity=Severity.CRITICAL,
            response_time_ms=None,
            status_code=None,
            message=f"HTTP check failed: {exc}",
            details={"url": url},
        )


async def check_tcp(target: str, port: int, timeout_seconds: int) -> ServiceProbeResult:
    started = perf_counter()

    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=timeout_seconds)
        writer.close()
        await writer.wait_closed()
        duration = (perf_counter() - started) * 1000
        return ServiceProbeResult(
            status=ServerStatus.ONLINE,
            severity=Severity.INFO,
            response_time_ms=duration,
            status_code=None,
            message=f"TCP port {port} is reachable",
            details={"target": target, "port": port},
        )
    except (asyncio.TimeoutError, OSError) as exc:
        return ServiceProbeResult(
            status=ServerStatus.OFFLINE,
            severity=Severity.CRITICAL,
            response_time_ms=None,
            status_code=None,
            message=f"TCP port {port} is unavailable: {exc}",
            details={"target": target, "port": port},
        )


def _fetch_ssl_certificate(target: str, port: int, timeout_seconds: int) -> dict:
    hostname = urlparse(target).hostname if "://" in target else target
    hostname = hostname or target

    context = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout_seconds) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
            return secure_sock.getpeercert()


async def check_ssl_expiry(target: str, port: int, timeout_seconds: int, warning_days: int) -> ServiceProbeResult:
    try:
        certificate = await asyncio.to_thread(_fetch_ssl_certificate, target, port, timeout_seconds)
        not_after = certificate.get("notAfter")
        if not not_after:
            return ServiceProbeResult(
                status=ServerStatus.DEGRADED,
                severity=Severity.WARNING,
                response_time_ms=None,
                status_code=None,
                message="SSL certificate does not expose notAfter",
                details={"target": target, "port": port},
            )

        expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = (expires_at - datetime.now(timezone.utc)).days

        if days_left < 0:
            return ServiceProbeResult(
                status=ServerStatus.OFFLINE,
                severity=Severity.CRITICAL,
                response_time_ms=None,
                status_code=None,
                message=f"SSL certificate expired {-days_left} days ago",
                details={"target": target, "port": port, "days_left": days_left},
            )

        if days_left <= warning_days:
            return ServiceProbeResult(
                status=ServerStatus.DEGRADED,
                severity=Severity.WARNING,
                response_time_ms=None,
                status_code=None,
                message=f"SSL certificate expires in {days_left} days",
                details={"target": target, "port": port, "days_left": days_left},
            )

        return ServiceProbeResult(
            status=ServerStatus.ONLINE,
            severity=Severity.INFO,
            response_time_ms=None,
            status_code=None,
            message=f"SSL certificate is valid for {days_left} more days",
            details={"target": target, "port": port, "days_left": days_left},
        )
    except Exception as exc:
        return ServiceProbeResult(
            status=ServerStatus.OFFLINE,
            severity=Severity.CRITICAL,
            response_time_ms=None,
            status_code=None,
            message=f"SSL check failed: {exc}",
            details={"target": target, "port": port},
        )

