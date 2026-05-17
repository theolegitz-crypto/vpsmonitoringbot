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
  return `${Number(value || 0).toFixed(1)}%`;
}

export function formatLatency(value) {
  return `${Number(value || 0).toFixed(1)} ms`;
}

export function formatDate(value) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}

