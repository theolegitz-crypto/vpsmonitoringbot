import asyncio
import base64
import hashlib
import json
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.app.core.config import settings
from backend.app.schemas.agent import AgentMetricPayload, ContainerMetricPayload
from backend.app.schemas.speed_test import AgentSpeedTestCompleteRequest


REMOTE_METRICS_SCRIPT = r"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time


def parse_meminfo():
    values = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0])
    return values


def parse_network_totals():
    rx_total = 0
    tx_total = 0
    with open("/proc/net/dev", "r", encoding="utf-8") as handle:
        for line in handle.readlines()[2:]:
            name, raw = line.split(":", 1)
            interface = name.strip()
            if interface == "lo":
                continue
            parts = raw.split()
            rx_total += int(parts[0])
            tx_total += int(parts[8])
    return rx_total, tx_total


def parse_cpu_percent():
    def sample():
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            parts = handle.readline().split()[1:]
        values = [int(item) for item in parts]
        idle = values[3] + values[4]
        total = sum(values)
        return idle, total

    idle_1, total_1 = sample()
    time.sleep(0.25)
    idle_2, total_2 = sample()
    total_delta = max(total_2 - total_1, 1)
    idle_delta = max(idle_2 - idle_1, 0)
    return round(100.0 * (1.0 - (idle_delta / total_delta)), 2)


def parse_size_to_mb(raw):
    if not raw:
        return None
    value = raw.strip()
    if value in {"0B", "0", "-"}:
        return 0.0
    suffixes = {
        "b": 1 / (1024 * 1024),
        "kib": 1 / 1024,
        "kb": 1000 / (1024 * 1024),
        "mib": 1,
        "mb": 1000 * 1000 / (1024 * 1024),
        "gib": 1024,
        "gb": 1000 * 1000 * 1000 / (1024 * 1024),
        "tib": 1024 * 1024,
        "tb": 1000 * 1000 * 1000 * 1000 / (1024 * 1024),
    }
    lower = value.lower()
    for suffix, multiplier in sorted(suffixes.items(), key=lambda item: len(item[0]), reverse=True):
        if lower.endswith(suffix):
            number = float(lower[: -len(suffix)].strip())
            return round(number * multiplier, 2)
    return round(float(value) / (1024 * 1024), 2)


def parse_percent(raw):
    if not raw:
        return None
    value = raw.strip().replace("%", "")
    if not value or value == "-":
        return None
    return round(float(value), 2)


def parse_memory_usage(raw):
    if not raw or "/" not in raw:
        return None, None
    left, right = [item.strip() for item in raw.split("/", 1)]
    return parse_size_to_mb(left), parse_size_to_mb(right)


def collect_containers():
    if os.environ.get("SWAGMONITOR_COLLECT_DOCKER", "1") != "1":
        return [], {"enabled": False, "reason": "disabled"}

    docker_bin = shutil.which("docker")
    if not docker_bin:
        return [], {"enabled": False, "reason": "docker-not-found"}

    ids_result = subprocess.run([docker_bin, "ps", "-aq"], capture_output=True, text=True)
    if ids_result.returncode != 0:
        return [], {
            "enabled": True,
            "available": False,
            "reason": ids_result.stderr.strip() or ids_result.stdout.strip() or "docker-ps-failed",
        }

    container_ids = [item.strip() for item in ids_result.stdout.splitlines() if item.strip()]
    if not container_ids:
        return [], {"enabled": True, "available": True, "count": 0}

    inspect_result = subprocess.run(
        [docker_bin, "inspect", *container_ids],
        capture_output=True,
        text=True,
    )
    if inspect_result.returncode != 0:
        return [], {
            "enabled": True,
            "available": False,
            "reason": inspect_result.stderr.strip() or inspect_result.stdout.strip() or "docker-inspect-failed",
        }

    stats_map = {}
    stats_result = subprocess.run(
        [docker_bin, "stats", "--no-stream", "--format", "{{json .}}"],
        capture_output=True,
        text=True,
    )
    if stats_result.returncode == 0:
        for line in stats_result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = payload.get("ID") or payload.get("Container")
            if key:
                stats_map[key] = payload

    inspected = json.loads(inspect_result.stdout)
    containers = []
    for item in inspected:
        container_id = item.get("Id", "")
        short_id = container_id[:12]
        name = (item.get("Name") or "").lstrip("/") or short_id
        state_info = item.get("State") or {}
        stats = stats_map.get(container_id) or stats_map.get(short_id)
        if stats is None:
            for key, payload in stats_map.items():
                if container_id.startswith(key):
                    stats = payload
                    break

        memory_usage_mb, memory_limit_mb = parse_memory_usage(stats.get("MemUsage") if stats else None)
        containers.append(
            {
                "container_id": container_id,
                "name": name,
                "image": ((item.get("Config") or {}).get("Image")),
                "state": state_info.get("Status"),
                "status": state_info.get("Status"),
                "health_status": ((state_info.get("Health") or {}).get("Status")),
                "restart_count": item.get("RestartCount"),
                "cpu_percent": parse_percent(stats.get("CPUPerc") if stats else None),
                "memory_usage_mb": memory_usage_mb,
                "memory_limit_mb": memory_limit_mb,
                "memory_percent": parse_percent(stats.get("MemPerc") if stats else None),
                "details": {
                    "names": item.get("Name"),
                    "running": state_info.get("Running"),
                },
            }
        )

    return containers, {"enabled": True, "available": True, "count": len(containers)}


def main():
    disk_path = os.environ.get("SWAGMONITOR_DISK_PATH", "/") or "/"
    meminfo = parse_meminfo()
    mem_total_mb = round(meminfo.get("MemTotal", 0) / 1024, 2)
    mem_available_mb = round(meminfo.get("MemAvailable", 0) / 1024, 2)
    mem_used_mb = round(max(mem_total_mb - mem_available_mb, 0.0), 2)
    swap_total_mb = round(meminfo.get("SwapTotal", 0) / 1024, 2)
    swap_free_mb = round(meminfo.get("SwapFree", 0) / 1024, 2)
    swap_used_mb = round(max(swap_total_mb - swap_free_mb, 0.0), 2)
    memory_percent = round((mem_used_mb / mem_total_mb) * 100, 2) if mem_total_mb else None
    swap_percent = round((swap_used_mb / swap_total_mb) * 100, 2) if swap_total_mb else None

    stat = os.statvfs(disk_path)
    disk_total_gb = round((stat.f_frsize * stat.f_blocks) / (1024 ** 3), 2)
    disk_available_gb = round((stat.f_frsize * stat.f_bavail) / (1024 ** 3), 2)
    disk_used_gb = round(max(disk_total_gb - disk_available_gb, 0.0), 2)
    disk_percent = round((disk_used_gb / disk_total_gb) * 100, 2) if disk_total_gb else None

    with open("/proc/loadavg", "r", encoding="utf-8") as handle:
        load_parts = handle.read().strip().split()
    with open("/proc/uptime", "r", encoding="utf-8") as handle:
        uptime_seconds = int(float(handle.read().strip().split()[0]))

    net_rx_bytes, net_tx_bytes = parse_network_totals()
    containers, docker_details = collect_containers()

    payload = {
        "metrics": {
            "cpu_percent": parse_cpu_percent(),
            "memory_percent": memory_percent,
            "memory_used_mb": mem_used_mb,
            "memory_total_mb": mem_total_mb,
            "swap_percent": swap_percent,
            "swap_used_mb": swap_used_mb,
            "swap_total_mb": swap_total_mb,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "load_1": round(float(load_parts[0]), 2),
            "load_5": round(float(load_parts[1]), 2),
            "load_15": round(float(load_parts[2]), 2),
            "net_rx_bytes": net_rx_bytes,
            "net_tx_bytes": net_tx_bytes,
            "uptime_seconds": uptime_seconds,
            "details": {
                "source": "ssh",
                "disk_path": disk_path,
                "hostname": socket.gethostname(),
                "python": sys.executable,
                "docker": docker_details,
            },
        },
        "containers": containers,
    }
    print(json.dumps(payload, separators=(",", ":")))


if __name__ == "__main__":
    main()
"""


REMOTE_SPEEDTEST_SCRIPT = r"""
import json
import os
import shutil
import subprocess


def parse_number(value):
    if value is None:
        return None
    return round(float(value), 2)


def parse_ookla(payload):
    server = payload.get("server") or {}
    ping = payload.get("ping") or {}
    download = payload.get("download") or {}
    upload = payload.get("upload") or {}
    bandwidth_down = download.get("bandwidth")
    bandwidth_up = upload.get("bandwidth")
    return {
        "status": "completed",
        "provider_name": server.get("name") or server.get("host"),
        "provider_location": ", ".join(
            item for item in [server.get("location"), server.get("country")] if item
        ) or None,
        "external_ip": ((payload.get("interface") or {}).get("externalIp")),
        "download_mbps": round((float(bandwidth_down) * 8) / 1_000_000, 2) if bandwidth_down else None,
        "upload_mbps": round((float(bandwidth_up) * 8) / 1_000_000, 2) if bandwidth_up else None,
        "ping_ms": parse_number(ping.get("latency")),
        "jitter_ms": parse_number(ping.get("jitter")),
        "details": {"source": "ssh", "tool": "speedtest"},
        "error": None,
    }


def parse_speedtest_cli(payload):
    server = payload.get("server") or {}
    client = payload.get("client") or {}
    return {
        "status": "completed",
        "provider_name": server.get("sponsor") or server.get("name"),
        "provider_location": ", ".join(
            item for item in [server.get("name"), server.get("country")] if item
        ) or None,
        "external_ip": client.get("ip"),
        "download_mbps": round(float(payload.get("download", 0)) / 1_000_000, 2) if payload.get("download") else None,
        "upload_mbps": round(float(payload.get("upload", 0)) / 1_000_000, 2) if payload.get("upload") else None,
        "ping_ms": parse_number(payload.get("ping")),
        "jitter_ms": None,
        "details": {"source": "ssh", "tool": "speedtest-cli"},
        "error": None,
    }


def failure(message):
    print(json.dumps({"status": "failed", "error": message}, separators=(",", ":")))


def extract_json_payload(raw_output):
    text = (raw_output or "").strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None
    return None


def compact_output(value, limit=280):
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def run_tool(tool_name, command, parser, timeout):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"{tool_name} timed out"

    if result.returncode != 0:
        context = compact_output(result.stderr) or compact_output(result.stdout) or f"{tool_name} failed"
        return None, context

    payload = extract_json_payload(result.stdout)
    if payload is None:
        stdout_preview = compact_output(result.stdout)
        stderr_preview = compact_output(result.stderr)
        context = stdout_preview or stderr_preview or "no output"
        return None, f"{tool_name} returned invalid JSON. Output: {context}"

    try:
        return parser(payload), None
    except Exception as exc:
        return None, f"{tool_name} payload parse failed: {exc}"


def main():
    timeout = int(os.environ.get("SWAGMONITOR_SPEEDTEST_TIMEOUT", "180"))
    speedtest_bin = shutil.which("speedtest")
    speedtest_cli_bin = shutil.which("speedtest-cli")

    candidates = []
    if speedtest_bin:
        candidates.append(
            (
                "speedtest",
                [speedtest_bin, "--accept-license", "--accept-gdpr", "--format=json"],
                parse_ookla,
            )
        )
    if speedtest_cli_bin:
        candidates.append(
            (
                "speedtest-cli",
                [speedtest_cli_bin, "--json"],
                parse_speedtest_cli,
            )
        )

    if not candidates:
        failure("Neither speedtest nor speedtest-cli is installed on the VPS. Install it with: apt install -y speedtest-cli")
        return

    errors = []
    for tool_name, command, parser in candidates:
        payload, error = run_tool(tool_name, command, parser, timeout)
        if payload is not None:
            print(json.dumps(payload, separators=(",", ":")))
            return
        if error:
            errors.append(error)

    failure(" | ".join(errors) if errors else "Remote speed test failed")


if __name__ == "__main__":
    main()
"""


@dataclass(slots=True)
class RemoteMetricsSnapshot:
    metrics: AgentMetricPayload
    containers: list[ContainerMetricPayload]
    recorded_at: datetime


class SshRemoteService:
    def encrypt_password(self, password: str | None) -> str | None:
        normalized = (password or "").strip()
        if not normalized:
            return None
        fernet = self._build_fernet()
        return fernet.encrypt(normalized.encode("utf-8")).decode("utf-8")

    def decrypt_password(self, encrypted_password: str | None) -> str | None:
        if not encrypted_password:
            return None
        fernet = self._build_fernet()
        try:
            decrypted = fernet.decrypt(encrypted_password.encode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Unable to decrypt SSH password with the configured SSH_CREDENTIALS_KEY") from exc
        return decrypted.decode("utf-8")

    async def collect_metrics(self, server) -> RemoteMetricsSnapshot:
        payload = await self._run_remote_json(
            server,
            REMOTE_METRICS_SCRIPT,
            timeout_seconds=settings.ssh_command_timeout_seconds,
            environment={
                "SWAGMONITOR_DISK_PATH": "/",
                "SWAGMONITOR_COLLECT_DOCKER": "1" if server.ssh_collect_docker else "0",
            },
        )
        return RemoteMetricsSnapshot(
            metrics=AgentMetricPayload.model_validate(payload.get("metrics") or {}),
            containers=[
                ContainerMetricPayload.model_validate(item)
                for item in (payload.get("containers") or [])
            ],
            recorded_at=datetime.now(timezone.utc),
        )

    async def run_speed_test(self, server, progress_callback=None, should_cancel=None) -> AgentSpeedTestCompleteRequest:
        if progress_callback:
            await progress_callback(12, "Preparing SSH speed test")
        payload = await self._run_remote_json(
            server,
            REMOTE_SPEEDTEST_SCRIPT,
            timeout_seconds=settings.ssh_speed_test_timeout_seconds,
            environment={
                "SWAGMONITOR_SPEEDTEST_TIMEOUT": str(settings.ssh_speed_test_timeout_seconds),
            },
            progress_callback=progress_callback,
            should_cancel=should_cancel,
        )
        result = self._normalize_speed_test_payload(payload)
        if progress_callback:
            await progress_callback(
                100,
                "Completed" if result.status == "completed" else "Failed",
            )
        return result

    async def _run_remote_json(
        self,
        server,
        script: str,
        *,
        timeout_seconds: int,
        environment: dict[str, str],
        progress_callback=None,
        should_cancel=None,
    ) -> dict[str, Any]:
        asyncssh = self._load_asyncssh()
        password = self.decrypt_password(server.ssh_password_encrypted)
        host = self._resolve_host(server)
        username = (server.ssh_username or "").strip()

        if not server.ssh_enabled:
            raise RuntimeError(f"SSH is disabled for {server.name}")
        if not username:
            raise RuntimeError(f"SSH username is not configured for {server.name}")
        if not password:
            raise RuntimeError(f"SSH password is not configured for {server.name}")

        connect_kwargs = {
            "host": host,
            "port": server.ssh_port or 22,
            "username": username,
            "password": password,
            "connect_timeout": settings.ssh_connect_timeout_seconds,
        }
        if settings.ssh_allow_unknown_hosts:
            connect_kwargs["known_hosts"] = None

        command = self._build_remote_python_command(script, environment)
        if progress_callback:
            await progress_callback(20, "Connecting to the VPS")
        try:
            connection = await asyncssh.connect(**connect_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"SSH connection to {host}:{server.ssh_port or 22} failed for {server.name}: {exc}"
            ) from exc
        progress_task = None
        try:
            async with connection:
                if progress_callback:
                    await progress_callback(32, "Starting remote command")
                    progress_task = asyncio.create_task(
                        self._simulate_speedtest_progress(progress_callback, timeout_seconds)
                    )
                run_task = asyncio.create_task(connection.run(command, check=False))
                try:
                    result = await self._await_remote_result(
                        run_task,
                        timeout_seconds + settings.ssh_connect_timeout_seconds,
                        should_cancel=should_cancel,
                    )
                finally:
                    if not run_task.done():
                        run_task.cancel()
        finally:
            if progress_task:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.exit_status != 0:
            raise RuntimeError(stderr or stdout or f"Remote command failed with exit code {result.exit_status}")

        return self._parse_remote_json(stdout)

    @staticmethod
    def _parse_remote_json(stdout: str) -> dict[str, Any]:
        if not stdout:
            raise RuntimeError("Remote command returned no data")

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise RuntimeError("Remote command did not return valid JSON")

    @staticmethod
    def _normalize_speed_test_payload(payload: dict[str, Any]) -> AgentSpeedTestCompleteRequest:
        if "status" in payload:
            error = payload.get("error")
            if isinstance(error, dict):
                payload = {**payload, "error": error.get("error") or json.dumps(error, ensure_ascii=False)}
            return AgentSpeedTestCompleteRequest.model_validate(payload)

        raw_error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(raw_error, dict):
            error_text = raw_error.get("error") or json.dumps(raw_error, ensure_ascii=False)
        elif raw_error:
            error_text = str(raw_error)
        else:
            error_text = "Remote speed test failed"

        return AgentSpeedTestCompleteRequest(
            status="failed",
            error=error_text[:500],
            details={"source": "ssh", "raw": payload},
        )

    @staticmethod
    async def _simulate_speedtest_progress(progress_callback, timeout_seconds: int) -> None:
        elapsed = 0
        step = 3
        while True:
            await asyncio.sleep(step)
            elapsed += step
            ratio = min(elapsed / max(timeout_seconds, 1), 0.98)
            if ratio < 0.18:
                percent = 40
                stage = "Testing latency"
            elif ratio < 0.72:
                percent = min(78, 40 + int(((ratio - 0.18) / 0.54) * 38))
                stage = "Measuring download"
            else:
                percent = min(95, 78 + int(((ratio - 0.72) / 0.26) * 17))
                stage = "Measuring upload"
            await progress_callback(percent, stage)

    @staticmethod
    async def _await_remote_result(run_task, timeout_seconds: int, *, should_cancel=None):
        started = asyncio.get_running_loop().time()
        while True:
            if run_task.done():
                return await run_task
            if should_cancel and await should_cancel():
                run_task.cancel()
                raise asyncio.CancelledError
            if asyncio.get_running_loop().time() - started > timeout_seconds:
                run_task.cancel()
                raise asyncio.TimeoutError
            await asyncio.sleep(1)

    @staticmethod
    def _build_remote_python_command(script: str, environment: dict[str, str]) -> str:
        encoded_script = base64.b64encode(script.encode("utf-8")).decode("ascii")
        loader = f"import base64;exec(base64.b64decode('{encoded_script}').decode('utf-8'))"
        env_prefix = " ".join(
            f"{key}={shlex.quote(value)}"
            for key, value in environment.items()
        )
        python_loader = shlex.quote(loader)
        python_chain = f"python3 -c {python_loader} || python -c {python_loader}"
        inner_command = f"{env_prefix} {python_chain}".strip()
        return f"sh -lc {shlex.quote(inner_command)}"

    @staticmethod
    def _resolve_host(server) -> str:
        host = (server.ssh_host or server.address or "").strip()
        if not host:
            raise RuntimeError(f"SSH host is not configured for {server.name}")
        return host

    @staticmethod
    def _load_asyncssh():
        try:
            import asyncssh
        except ImportError as exc:
            raise RuntimeError("The asyncssh package is not installed. Rebuild the backend image or reinstall backend requirements.") from exc
        return asyncssh

    @staticmethod
    def _build_fernet():
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise RuntimeError("The cryptography package is not installed. Rebuild the backend image or reinstall backend requirements.") from exc

        raw_key = (settings.ssh_credentials_key or "").strip()
        if not raw_key:
            raise RuntimeError("SSH_CREDENTIALS_KEY is not configured")

        try:
            if len(raw_key) == 44:
                base64.urlsafe_b64decode(raw_key.encode("ascii"))
                return Fernet(raw_key.encode("ascii"))
        except Exception:
            pass

        derived_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        return Fernet(derived_key)
