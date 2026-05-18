import asyncio
import platform
import shutil
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

from backend.app.core.config import settings
from backend.app.models import CheckType, DiagnosticSnapshot, ServerStatus, Severity


def _extract_host(target: str) -> str:
    if "://" in target:
        return (urlparse(target).hostname or target).strip()
    return target.strip()


def _safe_dict(input_details: dict | None) -> dict:
    return input_details.copy() if isinstance(input_details, dict) else {}


class DiagnosticService:
    def __init__(self, session):
        self.session = session

    async def capture_server_failure(self, server, ping_stats, severity: Severity, message: str, retry_attempts: int) -> None:
        if not settings.diagnostics_enabled:
            return

        self.session.add(
            DiagnosticSnapshot(
                server_id=server.id,
                category="icmp",
                headline=f"ICMP snapshot for {server.name}",
                check_type=CheckType.ICMP,
                status=server.status,
                severity=severity,
                details={
                    "message": message,
                    "avg_latency_ms": ping_stats.avg_latency_ms,
                    "min_latency_ms": ping_stats.min_latency_ms,
                    "max_latency_ms": ping_stats.max_latency_ms,
                    "packet_loss": ping_stats.packet_loss,
                    "jitter_ms": ping_stats.jitter_ms,
                    "raw_output": ping_stats.raw_output,
                    "error": ping_stats.error,
                    "retry_attempts": retry_attempts,
                },
                created_at=datetime.now(timezone.utc),
            )
        )

        await self._append_dns_snapshot(
            server_id=server.id,
            service_check_id=None,
            target=server.address,
            check_type=CheckType.ICMP,
            severity=severity,
            status=server.status,
        )
        if ping_stats.error or ping_stats.packet_loss > 0 or server.status == ServerStatus.OFFLINE:
            await self._append_traceroute_snapshot(
                server_id=server.id,
                service_check_id=None,
                target=server.address,
                check_type=CheckType.ICMP,
                severity=severity,
                status=server.status,
            )

    async def capture_service_failure(self, service_check, result, retry_attempts: int) -> None:
        if not settings.diagnostics_enabled:
            return

        self.session.add(
            DiagnosticSnapshot(
                server_id=service_check.server_id,
                service_check_id=service_check.id,
                category=result.check_type.value if hasattr(result, "check_type") else "service",
                headline=f"{service_check.name} diagnostic snapshot",
                check_type=service_check.check_type,
                status=result.status,
                severity=result.severity,
                details={
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "status_code": result.status_code,
                    "details": _safe_dict(result.details),
                    "retry_attempts": retry_attempts,
                },
                created_at=datetime.now(timezone.utc),
            )
        )

        await self._append_dns_snapshot(
            server_id=service_check.server_id,
            service_check_id=service_check.id,
            target=service_check.target,
            check_type=service_check.check_type,
            severity=result.severity,
            status=result.status,
        )
        if result.status == ServerStatus.OFFLINE or result.severity == Severity.CRITICAL:
            await self._append_traceroute_snapshot(
                server_id=service_check.server_id,
                service_check_id=service_check.id,
                target=service_check.target,
                check_type=service_check.check_type,
                severity=result.severity,
                status=result.status,
            )

    async def _append_dns_snapshot(
        self,
        *,
        server_id: int | None,
        service_check_id: int | None,
        target: str,
        check_type,
        severity: Severity,
        status,
    ) -> None:
        host = _extract_host(target)
        if not host:
            return

        details = await asyncio.to_thread(self._resolve_host, host)
        self.session.add(
            DiagnosticSnapshot(
                server_id=server_id,
                service_check_id=service_check_id,
                category="dns",
                headline=f"DNS lookup for {host}",
                check_type=check_type,
                status=status,
                severity=severity if details.get("ok") else Severity.WARNING,
                details=details,
                created_at=datetime.now(timezone.utc),
            )
        )

    async def _append_traceroute_snapshot(
        self,
        *,
        server_id: int | None,
        service_check_id: int | None,
        target: str,
        check_type,
        severity: Severity,
        status,
    ) -> None:
        if not settings.traceroute_enabled:
            return

        host = _extract_host(target)
        if not host:
            return

        details = await self._run_traceroute(host)
        if not details:
            return

        self.session.add(
            DiagnosticSnapshot(
                server_id=server_id,
                service_check_id=service_check_id,
                category="traceroute",
                headline=f"Traceroute to {host}",
                check_type=check_type,
                status=status,
                severity=severity,
                details=details,
                created_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _resolve_host(host: str) -> dict:
        try:
            resolved = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            addresses = sorted({item[4][0] for item in resolved})
            return {"ok": True, "host": host, "addresses": addresses}
        except OSError as exc:
            return {"ok": False, "host": host, "error": str(exc)}

    async def _run_traceroute(self, host: str) -> dict | None:
        command = self._build_traceroute_command(host)
        if not command:
            return None

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        output = "\n".join(
            part.decode("utf-8", errors="ignore").strip()
            for part in (stdout, stderr)
            if part
        ).strip()
        return {
            "host": host,
            "command": command,
            "returncode": process.returncode,
            "output": output,
        }

    @staticmethod
    def _build_traceroute_command(host: str) -> list[str] | None:
        if platform.system().lower() == "windows":
            if shutil.which("tracert"):
                return ["tracert", "-h", str(settings.traceroute_max_hops), host]
            return None

        executable = shutil.which("traceroute") or shutil.which("tracepath")
        if not executable:
            return None

        if executable.endswith("tracepath"):
            return [executable, "-m", str(settings.traceroute_max_hops), host]

        return [
            executable,
            "-m",
            str(settings.traceroute_max_hops),
            "-w",
            str(settings.traceroute_timeout_seconds),
            host,
        ]
