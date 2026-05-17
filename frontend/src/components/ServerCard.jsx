import { Link } from "react-router-dom";
import { ArrowUpRight, RefreshCcw } from "lucide-react";

import { formatLatency, formatPercent } from "../lib/format";
import { StatusBadge } from "./StatusBadge";
import { StatusStrip } from "./StatusStrip";

export function ServerCard({ server, onRefresh }) {
  return (
    <div className="rounded-[2rem] border border-white/8 bg-panel/85 p-5 shadow-glow transition duration-300 hover:-translate-y-1">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-xl font-bold">{server.name}</h3>
            <StatusBadge status={server.status} />
          </div>
          <p className="mt-2 text-sm text-slate-400">{server.address}</p>
          <p className="mt-3 text-sm text-slate-300">{server.description || "No description yet."}</p>
        </div>
        <button
          type="button"
          onClick={() => onRefresh(server.id)}
          className="rounded-full border border-white/10 bg-white/5 p-3 text-slate-200 transition hover:bg-white/10"
        >
          <RefreshCcw size={16} />
        </button>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
        <div className="rounded-2xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">24h</p>
          <p className="mt-2 text-xl font-semibold">{formatPercent(server.uptime_24h)}</p>
        </div>
        <div className="rounded-2xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">7d</p>
          <p className="mt-2 text-xl font-semibold">{formatPercent(server.uptime_7d)}</p>
        </div>
        <div className="rounded-2xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Latency</p>
          <p className="mt-2 text-xl font-semibold">{formatLatency(server.last_latency_ms)}</p>
        </div>
        <div className="rounded-2xl bg-white/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Loss</p>
          <p className="mt-2 text-xl font-semibold">{formatPercent(server.last_packet_loss)}</p>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">History</p>
          <p className="text-xs text-slate-400">{server.history.length} last checks</p>
        </div>
        <StatusStrip history={server.history} />
      </div>

      <div className="mt-6 flex items-center justify-between">
        <div className="text-sm text-slate-400">{server.services.length} service checks attached</div>
        <Link
          to={`/servers/${server.id}`}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-accent/90"
        >
          Open details
          <ArrowUpRight size={15} />
        </Link>
      </div>
    </div>
  );
}

