import { statusColor } from "../lib/format";

export function StatusStrip({ history = [] }) {
  return (
    <div className="grid grid-cols-12 gap-1 md:grid-cols-16 xl:grid-cols-24">
      {history.map((point, index) => (
        <div
          key={`${point.timestamp}-${index}`}
          className={`status-rect w-full ${statusColor(point.status)}`}
          title={`${point.status} at ${new Date(point.timestamp).toLocaleString()}`}
        />
      ))}
    </div>
  );
}

