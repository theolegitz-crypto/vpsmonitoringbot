from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import AlertEvent, Incident, IncidentStatus, Severity, ServerStatus
from backend.app.services.notifier import TelegramNotifier


class AlertManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.notifier = TelegramNotifier()

    async def handle_server_transition(
        self,
        server,
        previous_status: ServerStatus,
        previous_issues: int,
        severity: Severity,
        message: str,
    ) -> None:
        title = f"Server {server.name}"
        await self._handle_transition(
            entity=server,
            entity_label=title,
            previous_status=previous_status,
            previous_issues=previous_issues,
            threshold=max(1, server.consecutive_alert_threshold),
            current_status=server.status,
            severity=severity,
            message=message,
        )

    async def handle_service_transition(
        self,
        service_check,
        previous_status: ServerStatus,
        previous_issues: int,
        severity: Severity,
        message: str,
    ) -> None:
        title = f"Check {service_check.name}"
        await self._handle_transition(
            entity=service_check,
            entity_label=title,
            previous_status=previous_status,
            previous_issues=previous_issues,
            threshold=max(1, service_check.consecutive_alert_threshold),
            current_status=service_check.status,
            severity=severity,
            message=message,
        )

    async def _handle_transition(
        self,
        entity,
        entity_label: str,
        previous_status: ServerStatus,
        previous_issues: int,
        threshold: int,
        current_status: ServerStatus,
        severity: Severity,
        message: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        open_incident = await self._get_open_incident(entity)

        if current_status == ServerStatus.ONLINE:
            if open_incident:
                open_incident.status = IncidentStatus.RESOLVED
                open_incident.resolved_at = now
                open_incident.last_seen_at = now
                sent = await self._emit_event(entity, Severity.INFO, "recovery", f"{entity_label} recovered")
                if sent is not None:
                    pass
            return

        if open_incident:
            open_incident.severity = severity
            open_incident.description = message
            open_incident.last_seen_at = now

        if previous_issues < threshold <= entity.consecutive_issues:
            incident = open_incident
            if not incident:
                incident = Incident(
                    server_id=getattr(entity, "server_id", None) or getattr(entity, "id", None),
                    service_check_id=getattr(entity, "id", None) if hasattr(entity, "server_id") else None,
                    severity=severity,
                    title=f"{entity_label} is {current_status.value}",
                    description=message,
                    status=IncidentStatus.OPEN,
                    started_at=now,
                    last_seen_at=now,
                )
                self.session.add(incident)
            else:
                incident.title = f"{entity_label} is {current_status.value}"
                incident.severity = severity
                incident.description = message
            await self._emit_event(
                entity,
                severity,
                "alert",
                f"{entity_label} status {current_status.value}: {message}",
            )

    async def _get_open_incident(self, entity) -> Incident | None:
        statement = select(Incident).where(Incident.status == IncidentStatus.OPEN)
        if hasattr(entity, "server_id"):
            statement = statement.where(Incident.service_check_id == entity.id)
        else:
            statement = statement.where(Incident.server_id == entity.id, Incident.service_check_id.is_(None))
        return await self.session.scalar(statement.order_by(Incident.started_at.desc()))

    async def _emit_event(self, entity, severity: Severity, event_type: str, message: str) -> bool | None:
        muted_until = getattr(entity, "muted_until", None)
        is_muted = muted_until is not None and muted_until > datetime.now(timezone.utc)

        event = AlertEvent(
            server_id=getattr(entity, "server_id", None) or getattr(entity, "id", None),
            service_check_id=getattr(entity, "id", None) if hasattr(entity, "server_id") else None,
            severity=severity,
            event_type=event_type,
            message=message,
            sent_to_telegram=False,
        )
        self.session.add(event)

        if is_muted:
            return None

        sent = await self.notifier.send(message)
        event.sent_to_telegram = sent
        return sent
