import asyncio
import os
import platform
import socket
from datetime import datetime, timezone

import httpx
import psutil
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import docker
except Exception:  # pragma: no cover - optional runtime dependency path
    docker = None

try:
    import speedtest
except Exception:  # pragma: no cover - optional runtime dependency path
    speedtest = None


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.agent", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    agent_backend_url: str = "http://127.0.0.1:8000"
    agent_shared_token: str = ""
    agent_server_name: str = ""
    agent_server_id: int | None = None
    agent_interval_seconds: int = 30
    agent_request_timeout_seconds: int = 10
    agent_enable_docker: bool = True
    agent_disk_path: str = "/"
    agent_run_once: bool = False
    agent_version: str = "1.0.0"
    agent_speedtest_enabled: bool = True
    agent_speedtest_timeout_seconds: int = 180


settings = AgentSettings()


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _collect_system_metrics() -> dict:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(settings.agent_disk_path)
    network = psutil.net_io_counters()

    try:
        load_1, load_5, load_15 = os.getloadavg()
    except (AttributeError, OSError):
        load_1 = load_5 = load_15 = None

    return {
        "cpu_percent": _round(psutil.cpu_percent(interval=0.2)),
        "memory_percent": _round(memory.percent),
        "memory_used_mb": _round(memory.used / 1024 / 1024),
        "memory_total_mb": _round(memory.total / 1024 / 1024),
        "swap_percent": _round(swap.percent),
        "swap_used_mb": _round(swap.used / 1024 / 1024),
        "swap_total_mb": _round(swap.total / 1024 / 1024),
        "disk_percent": _round(disk.percent),
        "disk_used_gb": _round(disk.used / 1024 / 1024 / 1024),
        "disk_total_gb": _round(disk.total / 1024 / 1024 / 1024),
        "load_1": _round(load_1),
        "load_5": _round(load_5),
        "load_15": _round(load_15),
        "net_rx_bytes": int(network.bytes_recv),
        "net_tx_bytes": int(network.bytes_sent),
        "uptime_seconds": int(datetime.now(timezone.utc).timestamp() - psutil.boot_time()),
        "details": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
        },
    }


def _docker_cpu_percent(stats: dict) -> float | None:
    try:
        cpu_total = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        prev_total = stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_total = stats["cpu_stats"]["system_cpu_usage"]
        prev_system_total = stats["precpu_stats"]["system_cpu_usage"]
        cpu_count = len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or [1])
        cpu_delta = cpu_total - prev_total
        system_delta = system_total - prev_system_total
        if cpu_delta <= 0 or system_delta <= 0:
            return 0.0
        return _round((cpu_delta / system_delta) * cpu_count * 100.0)
    except Exception:
        return None


def _collect_container_metrics() -> list[dict]:
    if not settings.agent_enable_docker or docker is None:
        return []

    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
    except Exception:
        return []

    payload: list[dict] = []
    for container in containers:
        try:
            inspect_data = container.attrs or {}
            state = inspect_data.get("State", {})
            stats = container.stats(stream=False)
            memory_usage = (stats.get("memory_stats", {}) or {}).get("usage")
            memory_limit = (stats.get("memory_stats", {}) or {}).get("limit")
            memory_percent = None
            if memory_usage and memory_limit:
                memory_percent = _round((memory_usage / memory_limit) * 100.0)

            payload.append(
                {
                    "container_id": container.id,
                    "name": container.name,
                    "image": (container.image.tags or [container.image.short_id])[0] if container.image else None,
                    "state": state.get("Status") or container.status,
                    "status": container.status,
                    "health_status": (state.get("Health") or {}).get("Status"),
                    "restart_count": inspect_data.get("RestartCount"),
                    "cpu_percent": _docker_cpu_percent(stats),
                    "memory_usage_mb": _round(memory_usage / 1024 / 1024) if memory_usage else None,
                    "memory_limit_mb": _round(memory_limit / 1024 / 1024) if memory_limit else None,
                    "memory_percent": memory_percent,
                    "details": {
                        "labels": inspect_data.get("Config", {}).get("Labels") or {},
                        "created": inspect_data.get("Created"),
                    },
                }
            )
        except Exception as exc:
            payload.append(
                {
                    "container_id": container.id,
                    "name": container.name,
                    "image": None,
                    "state": "unknown",
                    "status": "error",
                    "health_status": None,
                    "restart_count": None,
                    "cpu_percent": None,
                    "memory_usage_mb": None,
                    "memory_limit_mb": None,
                    "memory_percent": None,
                    "details": {"error": str(exc)},
                }
            )
    return payload


async def send_payload() -> None:
    if not settings.agent_shared_token:
        raise RuntimeError("AGENT_SHARED_TOKEN is required")
    if not settings.agent_server_name and not settings.agent_server_id:
        raise RuntimeError("Set AGENT_SERVER_NAME or AGENT_SERVER_ID")

    payload = {
        "server_id": settings.agent_server_id,
        "server_name": settings.agent_server_name or None,
        "agent_version": settings.agent_version,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "metrics": _collect_system_metrics(),
        "containers": _collect_container_metrics(),
    }
    endpoint = settings.agent_backend_url.rstrip("/") + "/api/agent/ingest"
    headers = {"X-Agent-Token": settings.agent_shared_token}

    async with httpx.AsyncClient(timeout=settings.agent_request_timeout_seconds) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())


async def claim_speed_test_task() -> dict | None:
    if not settings.agent_speedtest_enabled:
        return None

    endpoint = settings.agent_backend_url.rstrip("/") + "/api/agent/speed-tests/claim"
    headers = {"X-Agent-Token": settings.agent_shared_token}
    payload = {"server_id": settings.agent_server_id, "server_name": settings.agent_server_name or None}

    async with httpx.AsyncClient(timeout=settings.agent_request_timeout_seconds) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data or None


def _run_speedtest_sync() -> dict:
    if speedtest is None:
        raise RuntimeError("speedtest-cli is not installed")

    tester = speedtest.Speedtest(timeout=settings.agent_speedtest_timeout_seconds)
    tester.get_best_server()
    tester.download()
    tester.upload()
    results = tester.results.dict()
    server = results.get("server") or {}
    client = results.get("client") or {}

    return {
        "status": "completed",
        "provider_name": server.get("sponsor"),
        "provider_location": ", ".join(
            item for item in [server.get("name"), server.get("country")] if item
        )
        or None,
        "external_ip": client.get("ip"),
        "download_mbps": _round((results.get("download") or 0) / 1_000_000),
        "upload_mbps": _round((results.get("upload") or 0) / 1_000_000),
        "ping_ms": _round(results.get("ping")),
        "jitter_ms": _round((server.get("latency") if isinstance(server.get("latency"), (int, float)) else None)),
        "details": results,
        "error": None,
    }


async def complete_speed_test_task(task_id: int, payload: dict) -> None:
    endpoint = settings.agent_backend_url.rstrip("/") + f"/api/agent/speed-tests/{task_id}/complete"
    headers = {"X-Agent-Token": settings.agent_shared_token}

    async with httpx.AsyncClient(timeout=settings.agent_request_timeout_seconds) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        print(response.json())


async def process_speed_test_task() -> None:
    task = await claim_speed_test_task()
    if not task:
        return

    try:
        payload = await asyncio.to_thread(_run_speedtest_sync)
    except Exception as exc:
        payload = {
            "status": "failed",
            "provider_name": None,
            "provider_location": None,
            "external_ip": None,
            "download_mbps": None,
            "upload_mbps": None,
            "ping_ms": None,
            "jitter_ms": None,
            "details": None,
            "error": str(exc),
        }

    await complete_speed_test_task(task["id"], payload)


async def main() -> None:
    while True:
        try:
            await send_payload()
            await process_speed_test_task()
        except Exception as exc:
            print(f"agent send failed: {exc}")
        if settings.agent_run_once:
            return
        await asyncio.sleep(settings.agent_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
