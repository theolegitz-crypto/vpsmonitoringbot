from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.models import (
    AgentMetric,
    AlertEvent,
    CheckResult,
    CheckResultRollup,
    ContainerMetric,
    DiagnosticSnapshot,
    Incident,
    IncidentStatus,
    ServerStatus,
    SpeedTestResult,
)


class RetentionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def cleanup(self) -> dict[str, int]:
        async with self.session_factory() as session:
            summary = {
                "check_results": await self._rollup_and_delete_old_results(session),
                "agent_metrics": await self._delete_older_than(
                    session,
                    AgentMetric,
                    AgentMetric.recorded_at,
                    settings.agent_metrics_retention_days,
                ),
                "container_metrics": await self._delete_older_than(
                    session,
                    ContainerMetric,
                    ContainerMetric.recorded_at,
                    settings.container_metrics_retention_days,
                ),
                "diagnostics": await self._delete_older_than(
                    session,
                    DiagnosticSnapshot,
                    DiagnosticSnapshot.created_at,
                    settings.diagnostic_retention_days,
                ),
                "speed_tests": await self._delete_older_than(
                    session,
                    SpeedTestResult,
                    SpeedTestResult.created_at,
                    settings.speed_test_retention_days,
                ),
                "alert_events": await self._delete_older_than(
                    session,
                    AlertEvent,
                    AlertEvent.created_at,
                    settings.alert_events_retention_days,
                ),
                "resolved_incidents": await self._delete_resolved_incidents(session),
                "check_result_rollups": await self._delete_older_than(
                    session,
                    CheckResultRollup,
                    CheckResultRollup.created_at,
                    settings.check_result_rollup_retention_days,
                ),
            }
            await session.commit()
            return summary

    async def _rollup_and_delete_old_results(self, session: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.check_results_retention_days)
        results = (
            await session.scalars(select(CheckResult).where(CheckResult.checked_at < cutoff))
        ).all()
        if not results:
            return 0

        grouped: dict[tuple, dict] = defaultdict(
            lambda: {
                "total": 0,
                "online": 0,
                "degraded": 0,
                "offline": 0,
                "unknown": 0,
                "latency_sum": 0.0,
                "latency_count": 0,
                "packet_loss_sum": 0.0,
                "packet_loss_count": 0,
                "response_sum": 0.0,
                "response_count": 0,
            }
        )

        for result in results:
            key = (
                result.server_id,
                result.service_check_id,
                result.check_type,
                result.checked_at.date(),
            )
            bucket = grouped[key]
            bucket["total"] += 1
            if result.status == ServerStatus.ONLINE:
                bucket["online"] += 1
            elif result.status == ServerStatus.DEGRADED:
                bucket["degraded"] += 1
            elif result.status == ServerStatus.OFFLINE:
                bucket["offline"] += 1
            else:
                bucket["unknown"] += 1

            if result.avg_latency_ms is not None:
                bucket["latency_sum"] += result.avg_latency_ms
                bucket["latency_count"] += 1
            if result.packet_loss is not None:
                bucket["packet_loss_sum"] += result.packet_loss
                bucket["packet_loss_count"] += 1
            if result.response_time_ms is not None:
                bucket["response_sum"] += result.response_time_ms
                bucket["response_count"] += 1

        for (server_id, service_check_id, check_type, bucket_date), values in grouped.items():
            existing = await session.scalar(
                select(CheckResultRollup).where(
                    CheckResultRollup.server_id == server_id,
                    CheckResultRollup.service_check_id == service_check_id,
                    CheckResultRollup.check_type == check_type,
                    CheckResultRollup.bucket_date == bucket_date,
                )
            )

            avg_latency = (
                values["latency_sum"] / values["latency_count"] if values["latency_count"] else None
            )
            avg_packet_loss = (
                values["packet_loss_sum"] / values["packet_loss_count"] if values["packet_loss_count"] else None
            )
            avg_response = (
                values["response_sum"] / values["response_count"] if values["response_count"] else None
            )

            if existing:
                existing.total_checks += values["total"]
                existing.online_checks += values["online"]
                existing.degraded_checks += values["degraded"]
                existing.offline_checks += values["offline"]
                existing.unknown_checks += values["unknown"]
                existing.avg_latency_ms = _weighted_average(
                    existing.avg_latency_ms,
                    existing.total_checks - values["total"],
                    avg_latency,
                    values["total"],
                )
                existing.avg_packet_loss = _weighted_average(
                    existing.avg_packet_loss,
                    existing.total_checks - values["total"],
                    avg_packet_loss,
                    values["total"],
                )
                existing.avg_response_time_ms = _weighted_average(
                    existing.avg_response_time_ms,
                    existing.total_checks - values["total"],
                    avg_response,
                    values["total"],
                )
            else:
                session.add(
                    CheckResultRollup(
                        server_id=server_id,
                        service_check_id=service_check_id,
                        check_type=check_type,
                        bucket_date=bucket_date,
                        total_checks=values["total"],
                        online_checks=values["online"],
                        degraded_checks=values["degraded"],
                        offline_checks=values["offline"],
                        unknown_checks=values["unknown"],
                        avg_latency_ms=avg_latency,
                        avg_packet_loss=avg_packet_loss,
                        avg_response_time_ms=avg_response,
                    )
                )

        await session.execute(delete(CheckResult).where(CheckResult.id.in_([item.id for item in results])))
        return len(results)

    async def _delete_older_than(self, session: AsyncSession, model, field, retention_days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        result = await session.execute(delete(model).where(field < cutoff))
        return result.rowcount or 0

    async def _delete_resolved_incidents(self, session: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.resolved_incident_retention_days)
        result = await session.execute(
            delete(Incident).where(
                Incident.status == IncidentStatus.RESOLVED,
                Incident.resolved_at.is_not(None),
                Incident.resolved_at < cutoff,
            )
        )
        return result.rowcount or 0


def _weighted_average(
    current_value: float | None,
    current_weight: int,
    incoming_value: float | None,
    incoming_weight: int,
) -> float | None:
    if current_value is None:
        return incoming_value
    if incoming_value is None:
        return current_value
    total_weight = current_weight + incoming_weight
    if total_weight <= 0:
        return None
    return ((current_value * current_weight) + (incoming_value * incoming_weight)) / total_weight
