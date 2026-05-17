import asyncio
import platform
import re
import statistics
from dataclasses import dataclass


@dataclass
class PingStats:
    avg_latency_ms: float | None
    min_latency_ms: float | None
    max_latency_ms: float | None
    packet_loss: float
    jitter_ms: float | None
    raw_output: str
    error: str | None = None


def _extract_latency_samples(output: str) -> list[float]:
    samples: list[float] = []
    for raw in re.findall(r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms", output, flags=re.IGNORECASE):
        try:
            samples.append(float(raw))
        except ValueError:
            continue
    return samples


def _parse_windows_ping(output: str) -> PingStats:
    packet_loss_match = re.search(r"\((\d+)%\s*loss\)", output, flags=re.IGNORECASE)
    min_match = re.search(r"Minimum = (\d+)ms", output, flags=re.IGNORECASE)
    max_match = re.search(r"Maximum = (\d+)ms", output, flags=re.IGNORECASE)
    avg_match = re.search(r"Average = (\d+)ms", output, flags=re.IGNORECASE)

    samples = _extract_latency_samples(output)
    jitter = statistics.pstdev(samples) if len(samples) > 1 else 0.0

    return PingStats(
        avg_latency_ms=float(avg_match.group(1)) if avg_match else None,
        min_latency_ms=float(min_match.group(1)) if min_match else None,
        max_latency_ms=float(max_match.group(1)) if max_match else None,
        packet_loss=float(packet_loss_match.group(1)) if packet_loss_match else 100.0,
        jitter_ms=jitter,
        raw_output=output,
        error=None,
    )


def _parse_unix_ping(output: str) -> PingStats:
    packet_loss_match = re.search(r"(\d+(?:\.\d+)?)%\s*packet loss", output, flags=re.IGNORECASE)
    rtt_match = re.search(
        r"(?:rtt|round-trip).*?=\s*(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)",
        output,
        flags=re.IGNORECASE,
    )

    return PingStats(
        avg_latency_ms=float(rtt_match.group(2)) if rtt_match else None,
        min_latency_ms=float(rtt_match.group(1)) if rtt_match else None,
        max_latency_ms=float(rtt_match.group(3)) if rtt_match else None,
        packet_loss=float(packet_loss_match.group(1)) if packet_loss_match else 100.0,
        jitter_ms=float(rtt_match.group(4)) if rtt_match else None,
        raw_output=output,
        error=None,
    )


async def run_icmp_ping(host: str, attempts: int, timeout: int) -> PingStats:
    system = platform.system().lower()
    if system == "windows":
        command = ["ping", "-n", str(attempts), "-w", str(timeout * 1000), host]
    else:
        command = ["ping", "-c", str(attempts), "-W", str(timeout), host]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    output = "\n".join(part.decode("utf-8", errors="ignore") for part in (stdout, stderr) if part)

    if process.returncode != 0 and not output:
        return PingStats(
            avg_latency_ms=None,
            min_latency_ms=None,
            max_latency_ms=None,
            packet_loss=100.0,
            jitter_ms=None,
            raw_output="",
            error=f"ping exited with code {process.returncode}",
        )

    stats = _parse_windows_ping(output) if system == "windows" else _parse_unix_ping(output)
    if process.returncode != 0 and stats.packet_loss >= 100:
        stats.error = "host unreachable"
    return stats

