import { statusTone } from "../lib/format";

export function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium uppercase tracking-[0.2em] ring-1 ${statusTone(
        status,
      )}`}
    >
      {status}
    </span>
  );
}

