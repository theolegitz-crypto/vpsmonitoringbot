import { statusColor } from "../lib/format";

export function StatusStrip({ history = [], maxVisible = 24, compact = false, align = "start" }) {
  const visibleHistory = history.slice(-maxVisible);
  const alignmentClass = align === "end" ? "justify-end" : "justify-start";
  const squareSizeClass = compact ? "h-2.5 w-2.5" : "h-3 w-3";

  return (
    <div className={`flex max-w-[15rem] items-center ${alignmentClass} gap-0.5 overflow-hidden`}>
      {visibleHistory.map((point, index) => (
        <div
          key={`${point.timestamp}-${index}`}
          className={`status-rect ${squareSizeClass} shrink-0 ${statusColor(point.status)}`}
          title={`${point.status} at ${new Date(point.timestamp).toLocaleString()}`}
        />
      ))}
    </div>
  );
}
