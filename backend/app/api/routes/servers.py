from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.session import AsyncSessionLocal
from backend.app.models import CheckType, Server, ServiceCheck
from backend.app.schemas.common import HistoryPoint, MessageResponse
from backend.app.schemas.server import MuteRequest, ServerCard, ServerCreate, ServerDetail, ServerRead, ServerUpdate
from backend.app.schemas.speed_test import SpeedTestQueueResponse, SpeedTestRead
from backend.app.schemas.service_check import ServiceCheckCreate, ServiceCheckRead, ServiceCheckUpdate
from backend.app.services.dashboard import DashboardService
from backend.app.services.monitoring import MonitoringService
from backend.app.services.server_management import apply_server_updates
from backend.app.services.speedtests import SpeedTestService
from backend.app.services.ssh_monitoring import SshMonitoringService
from backend.app.services.ssh_remote import SshRemoteService
from backend.app.utils.time import parse_duration


router = APIRouter(prefix="/servers", tags=["servers"])
dashboard_service = DashboardService(AsyncSessionLocal)
monitoring_service = MonitoringService(AsyncSessionLocal)
speed_test_service = SpeedTestService(AsyncSessionLocal)
ssh_monitoring_service = SshMonitoringService(AsyncSessionLocal)
ssh_remote_service = SshRemoteService()


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


@router.get("", response_model=list[ServerCard])
async def list_servers() -> list[ServerCard]:
    return await dashboard_service.list_servers()


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(payload: ServerCreate) -> ServerRead:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(Server).where(Server.name == payload.name))
        if existing:
            raise HTTPException(status_code=409, detail="Server with this name already exists")

        try:
            encrypted_password = ssh_remote_service.encrypt_password(payload.ssh_password)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        server = Server(
            name=payload.name,
            address=payload.address,
            description=payload.description,
            latency_warning_ms=payload.latency_warning_ms,
            latency_critical_ms=payload.latency_critical_ms,
            packet_loss_warning=payload.packet_loss_warning,
            packet_loss_critical=payload.packet_loss_critical,
            check_interval_seconds=payload.check_interval_seconds,
            consecutive_alert_threshold=payload.consecutive_alert_threshold,
            ssh_enabled=payload.ssh_enabled,
            ssh_host=_optional_text(payload.ssh_host),
            ssh_port=payload.ssh_port,
            ssh_username=_optional_text(payload.ssh_username),
            ssh_password_encrypted=encrypted_password,
            ssh_metrics_interval_seconds=payload.ssh_metrics_interval_seconds,
            ssh_collect_docker=payload.ssh_collect_docker,
            speed_test_enabled=payload.speed_test_enabled,
            speed_test_interval_seconds=payload.speed_test_interval_seconds,
        )
        session.add(server)
        await session.flush()

        for item in payload.service_checks:
            service_check = ServiceCheck(
                server_id=server.id,
                name=item.name,
                check_type=item.check_type,
                target=item.target,
                port=item.port,
                path=item.path,
                expected_status=item.expected_status,
                timeout_seconds=item.timeout_seconds,
                interval_seconds=item.interval_seconds,
                ssl_expiry_warning_days=item.ssl_expiry_warning_days,
                consecutive_alert_threshold=item.consecutive_alert_threshold,
            )
            session.add(service_check)

        await session.commit()
        await session.refresh(server)
        return ServerRead.model_validate(server)


@router.get("/{server_id}", response_model=ServerDetail)
async def get_server(server_id: int) -> ServerDetail:
    detail = await dashboard_service.build_server_detail(server_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Server not found")
    return detail


@router.patch("/{server_id}", response_model=ServerRead)
async def update_server(server_id: int, payload: ServerUpdate) -> ServerRead:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        updates = payload.model_dump(exclude_unset=True)
        ssh_password = updates.pop("ssh_password", None)
        if "ssh_host" in updates:
            updates["ssh_host"] = _optional_text(updates["ssh_host"])
        if "ssh_username" in updates:
            updates["ssh_username"] = _optional_text(updates["ssh_username"])
        if ssh_password is not None:
            normalized_password = _optional_text(ssh_password)
            if normalized_password:
                try:
                    server.ssh_password_encrypted = ssh_remote_service.encrypt_password(normalized_password)
                except RuntimeError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            await apply_server_updates(session, server, updates)
        except ValueError as exc:
            detail = str(exc)
            raise HTTPException(
                status_code=409 if "already exists" in detail.lower() else 400,
                detail=detail,
            ) from exc

        await session.commit()
        await session.refresh(server)
        return ServerRead.model_validate(server)


@router.delete("/{server_id}", response_model=MessageResponse)
async def delete_server(server_id: int) -> MessageResponse:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        await session.delete(server)
        await session.commit()
    return MessageResponse(message="Server deleted")


@router.post("/{server_id}/mute", response_model=MessageResponse)
async def mute_server(server_id: int, payload: MuteRequest) -> MessageResponse:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        server.muted_until = datetime.now(timezone.utc) + parse_duration(payload.duration)
        await session.commit()
    return MessageResponse(message=f"Muted until {server.muted_until.isoformat()}")


@router.post("/{server_id}/unmute", response_model=MessageResponse)
async def unmute_server(server_id: int) -> MessageResponse:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        server.muted_until = None
        await session.commit()
    return MessageResponse(message="Server unmuted")


@router.post("/{server_id}/run-check", response_model=ServerRead)
async def run_server_check(server_id: int) -> ServerRead:
    server = await monitoring_service.run_server_check(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerRead.model_validate(server)


@router.post("/{server_id}/collect-metrics", response_model=MessageResponse)
async def collect_server_metrics(server_id: int) -> MessageResponse:
    try:
        result = await ssh_monitoring_service.collect_server_metrics(server_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MessageResponse(
        message=(
            f"SSH metrics collected for {result.server_name} at {result.recorded_at.isoformat()}. "
            f"Containers received: {result.containers_received}"
        )
    )


@router.post("/{server_id}/speed-test", response_model=SpeedTestQueueResponse)
async def queue_speed_test(server_id: int) -> SpeedTestQueueResponse:
    try:
        speed_test, queued = await speed_test_service.queue_speed_test(server_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SpeedTestQueueResponse(
        queued=queued,
        speed_test=SpeedTestRead.model_validate(speed_test),
    )


@router.get("/{server_id}/speed-test/latest", response_model=SpeedTestRead | None)
async def latest_speed_test(server_id: int) -> SpeedTestRead | None:
    try:
        speed_test = await speed_test_service.latest_for_server(server_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SpeedTestRead.model_validate(speed_test) if speed_test else None


@router.get("/{server_id}/speed-tests", response_model=list[SpeedTestRead])
async def speed_test_history(server_id: int, limit: int = 10) -> list[SpeedTestRead]:
    try:
        items = await speed_test_service.list_for_server(server_id, limit=limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [SpeedTestRead.model_validate(item) for item in items]


@router.get("/{server_id}/history", response_model=list[HistoryPoint])
async def server_history(server_id: int, limit: int = 48) -> list[HistoryPoint]:
    return await dashboard_service.list_server_history(server_id, limit)


@router.post("/{server_id}/checks", response_model=ServiceCheckRead, status_code=status.HTTP_201_CREATED)
async def create_service_check(server_id: int, payload: ServiceCheckCreate) -> ServiceCheckRead:
    async with AsyncSessionLocal() as session:
        server = await session.get(Server, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        service_check = ServiceCheck(server_id=server.id, **payload.model_dump())
        session.add(service_check)
        await session.commit()
        await session.refresh(service_check)
        return ServiceCheckRead.model_validate(service_check)


@router.patch("/checks/{check_id}", response_model=ServiceCheckRead)
async def update_service_check(check_id: int, payload: ServiceCheckUpdate) -> ServiceCheckRead:
    async with AsyncSessionLocal() as session:
        service_check = await session.get(ServiceCheck, check_id)
        if not service_check:
            raise HTTPException(status_code=404, detail="Service check not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(service_check, field, value)

        await session.commit()
        await session.refresh(service_check)
        return ServiceCheckRead.model_validate(service_check)


@router.delete("/checks/{check_id}", response_model=MessageResponse)
async def delete_service_check(check_id: int) -> MessageResponse:
    async with AsyncSessionLocal() as session:
        service_check = await session.get(ServiceCheck, check_id)
        if not service_check:
            raise HTTPException(status_code=404, detail="Service check not found")
        await session.delete(service_check)
        await session.commit()
    return MessageResponse(message="Service check deleted")


@router.post("/checks/{check_id}/run", response_model=ServiceCheckRead)
async def run_service_check(check_id: int) -> ServiceCheckRead:
    service_check = await monitoring_service.run_service_check(check_id)
    if not service_check:
        raise HTTPException(status_code=404, detail="Service check not found")
    return ServiceCheckRead.model_validate(service_check)
