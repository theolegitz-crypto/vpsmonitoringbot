import { statusColor } from "../lib/format";

export function StatusStrip({ history = [] }) {
  return (
    <div className="flex items-center gap-1 overflow-hidden">
      {history.map((point, index) => (
        <div
          key={`${point.timestamp}-${index}`}
          className={`status-rect h-3 w-3 shrink-0 ${statusColor(point.status)}`}
          title={`${point.status} at ${new Date(point.timestamp).toLocaleString()}`}
        />
      ))}
    </div>
  );
}
