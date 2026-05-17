import { Link } from "react-router-dom";
import { Pencil, Play, Search, Trash2 } from "lucide-react";

import { formatPercent, statusTone } from "../lib/format";
import { StatusStrip } from "./StatusStrip";


export function MonitorTable({ rows, onRunServer, onRunService, onDeleteServer }) {
  return (
    <div className="overflow-x-auto rounded-[2rem] border border-white/8 bg-panel/88 shadow-glow">
      <table className="min-w-[1080px] w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-white/8 bg-white/5 text-left text-xs uppercase tracking-[0.2em] text-slate-400">
            <th className="px-5 py-4 font-medium">Monitor</th>
            <th className="px-5 py-4 font-medium">Type</th>
            <th className="px-5 py-4 font-medium">Status</th>
            <th className="px-5 py-4 font-medium">Target</th>
            <th className="px-5 py-4 font-medium">24h</th>
            <th className="px-5 py-4 font-medium">7d</th>
            <th className="px-5 py-4 font-medium">30d</th>
            <th className="px-5 py-4 font-medium">Current</th>
            <th className="px-5 py-4 font-medium">History</th>
            <th className="px-5 py-4 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-white/6 align-top last:border-b-0">
              <td className="px-5 py-4">
                <div className={row.kind === "service" ? "pl-5" : ""}>
                  <div className="font-medium text-slate-100">{row.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{row.note}</div>
                </div>
              </td>
              <td className="px-5 py-4 text-slate-300">{row.typeLabel}</td>
              <td className="px-5 py-4">
                <span className={`inline-flex rounded-full px-3 py-1 text-xs uppercase tracking-[0.16em] ring-1 ${statusTone(row.status)}`}>
                  {row.status}
                </span>
              </td>
              <td className="px-5 py-4 font-mono text-xs text-slate-300">{row.target}</td>
              <td className="px-5 py-4 text-slate-200">{formatPercent(row.uptime24h)}</td>
              <td className="px-5 py-4 text-slate-200">{formatPercent(row.uptime7d)}</td>
              <td className="px-5 py-4 text-slate-200">{formatPercent(row.uptime30d)}</td>
              <td className="px-5 py-4">
                <div className="text-slate-100">{row.currentPrimary}</div>
                <div className="mt-1 text-xs text-slate-500">{row.currentSecondary}</div>
              </td>
              <td className="px-5 py-4">
                <div className="w-[15rem]">
                  <StatusStrip history={row.history} maxVisible={24} compact align="end" />
                </div>
              </td>
              <td className="px-5 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => (row.kind === "server" ? onRunServer(row.runId) : onRunService(row.runId))}
                    className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/10"
                  >
                    <Play size={14} />
                    Run
                  </button>
                  <Link
                    to={row.link}
                    className="inline-flex items-center gap-2 rounded-full bg-accent px-3 py-2 text-xs font-medium text-slate-950 transition hover:bg-accent/90"
                  >
                    <Search size={14} />
                    Open
                  </Link>
                  {row.kind === "server" ? (
                    <Link
                      to={`${row.link}?edit=1`}
                      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/10"
                    >
                      <Pencil size={14} />
                      Edit
                    </Link>
                  ) : null}
                  {row.kind === "server" ? (
                    <button
                      type="button"
                      onClick={() => onDeleteServer?.(row.runId, row.name)}
                      className="inline-flex items-center gap-2 rounded-full border border-danger/30 bg-danger/10 px-3 py-2 text-xs font-medium text-red-100 transition hover:bg-danger/20"
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
