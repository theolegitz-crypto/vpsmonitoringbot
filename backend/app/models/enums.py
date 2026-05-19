from enum import Enum


class ServerStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CheckType(str, Enum):
    ICMP = "icmp"
    HTTP = "http"
    TCP = "tcp"
    SSL = "ssl"


class IncidentStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class SpeedTestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
