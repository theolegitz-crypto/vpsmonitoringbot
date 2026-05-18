export function statusTone(status) {
  switch (status) {
    case "online":
      return "bg-success/15 text-success ring-success/30";
    case "degraded":
      return "bg-warning/15 text-warning ring-warning/30";
    case "offline":
      return "bg-danger/15 text-danger ring-danger/30";
    default:
      return "bg-quiet/20 text-slate-300 ring-white/10";
  }
}

export function statusColor(status) {
  switch (status) {
    case "online":
      return "bg-success";
    case "degraded":
      return "bg-warning";
    case "offline":
      return "bg-danger";
    default:
      return "bg-slate-600";
  }
}

export function formatPercent(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${Number(value).toFixed(1)}%`;
}

export function formatLatency(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${Number(value).toFixed(1)} ms`;
}

export function formatDate(value) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}

export function formatBytes(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = Number(value);
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) {
    return "n/a";
  }

  const total = Math.max(0, Math.floor(Number(seconds)));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}
