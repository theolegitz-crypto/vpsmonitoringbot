from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import CheckType, Server, ServiceCheck


def _managed_name_for(check_type: CheckType, server_name: str, port: int | None = None) -> str | None:
    if check_type == CheckType.HTTP:
        return f"{server_name}-http"
    if check_type == CheckType.SSL:
        return f"{server_name}-ssl"
    if check_type == CheckType.TCP and port is not None:
        return f"{server_name}-tcp-{port}"
    return None


async def apply_server_updates(
    session: AsyncSession,
    server: Server,
    updates: Mapping[str, Any],
) -> Server:
    payload = dict(updates)
    if not payload:
        return server

    new_name = payload.get("name")
    if new_name and new_name.lower() != server.name.lower():
        existing = await session.scalar(
            select(Server).where(func.lower(Server.name) == new_name.lower(), Server.id != server.id)
        )
        if existing:
            raise ValueError("Server with this name already exists")

    old_name = server.name
    old_address = server.address

    for field, value in payload.items():
        setattr(server, field, value)

    checks = (await session.scalars(select(ServiceCheck).where(ServiceCheck.server_id == server.id))).all()

    if server.name != old_name:
        for check in checks:
            old_managed_name = _managed_name_for(check.check_type, old_name, check.port)
            new_managed_name = _managed_name_for(check.check_type, server.name, check.port)
            if old_managed_name and new_managed_name and check.name == old_managed_name:
                check.name = new_managed_name

    if server.address != old_address:
        for check in checks:
            if check.check_type == CheckType.TCP and check.target == old_address:
                check.target = server.address
        if payload.get("ssh_host") is None and server.ssh_host == old_address:
            server.ssh_host = server.address

    return server
