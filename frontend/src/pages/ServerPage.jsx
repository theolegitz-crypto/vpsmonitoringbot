import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, BellOff, BellRing, ShieldAlert } from "lucide-react";

import { api } from "../api/client";
import { MetricChart } from "../components/MetricChart";
import { StatusBadge } from "../components/StatusBadge";
import { StatusStrip } from "../components/StatusStrip";
import { formatDate, formatLatency, formatPercent } from "../lib/format";


export function ServerPage() {
  const { serverId } = useParams();
  const [server, setServer] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadServer() {
    try {
      setError("");
      const data = await api.server(serverId);
      setServer(data);
    } catch (loadError) {
      setError(loadError.message);
    }
  }

  useEffect(() => {
    loadServer();
  }, [serverId]);

  async function handleMuteToggle() {
    if (!server) {
      return;
    }
    setBusy(true);
    try {
      if (server.muted_until) {
        await api.unmuteServer(server.id);
      } else {
        await api.muteServer(server.id, "2h");
      }
      await loadServer();
    } catch (toggleError) {
      setError(toggleError.message);
    } finally {
      setBusy(false);
    }
  }

  if (!server) {
    return <div className="py-24 text-center text-slate-300">{error || "Loading server..."}</div>;
  }

  return (
    <div className="space-y-8">
      {error ? (
        <div className="rounded-3xl border border-danger/30 bg-danger/10 px-5 py-4 text-sm text-red-100">{error}</div>
      ) : null}

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-7 shadow-glow">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white">
              <ArrowLeft size={16} />
              Back to overview
            </Link>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-bold md:text-4xl">{server.name}</h1>
              <StatusBadge status={server.status} />
            </div>
            <p className="mt-3 font-mono text-sm text-slate-400">{server.address}</p>
            <p className="mt-3 max-w-2xl text-slate-300">{server.description || "No description provided."}</p>
          </div>
          <button
            type="button"
            onClick={handleMuteToggle}
            disabled={busy}
            className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium transition hover:bg-white/10 disabled:opacity-60"
          >
            {server.muted_until ? <BellRing size={16} /> : <BellOff size={16} />}
            {server.muted_until ? "Unmute alerts" : "Mute for 2 hours"}
          </button>
        </div>

        <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Status</p>
            <p className="mt-2 text-2xl font-semibold">{server.status}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Latency</p>
            <p className="mt-2 text-2xl font-semibold">{formatLatency(server.last_latency_ms)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Packet loss</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.last_packet_loss)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Jitter</p>
            <p className="mt-2 text-2xl font-semibold">{formatLatency(server.last_jitter_ms)}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 24h</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_24h)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 7d</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_7d)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 30d</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_30d)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Muted until</p>
            <p className="mt-2 text-sm font-medium text-slate-200">{server.muted_until ? formatDate(server.muted_until) : "Active"}</p>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Availability</p>
            <h2 className="mt-2 text-2xl font-bold">Server timeline</h2>
          </div>
          <p className="text-sm text-slate-400">Green OK, yellow degraded, red down, gray no data</p>
        </div>
        <StatusStrip history={server.history} />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <MetricChart data={server.latency_series} dataKey="latency" color="#45f0d1" label="Latency over time" />
        <MetricChart data={server.packet_loss_series} dataKey="packetloss" color="#f9a94b" label="Packet loss over time" />
      </section>

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Services</p>
          <h2 className="mt-2 text-2xl font-bold">Checks attached to this server</h2>
        </div>

        {server.services.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-[980px] w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/8 text-left text-xs uppercase tracking-[0.18em] text-slate-400">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Target</th>
                  <th className="px-4 py-3 font-medium">24h</th>
                  <th className="px-4 py-3 font-medium">Current</th>
                  <th className="px-4 py-3 font-medium">History</th>
                </tr>
              </thead>
              <tbody>
                {server.services.map((check) => (
                  <tr key={check.id} className="border-b border-white/6 last:border-b-0">
                    <td className="px-4 py-4 text-slate-100">{check.name}</td>
                    <td className="px-4 py-4 uppercase text-slate-300">{check.check_type}</td>
                    <td className="px-4 py-4"><StatusBadge status={check.status} /></td>
                    <td className="px-4 py-4 font-mono text-xs text-slate-300">
                      {check.target}{check.port ? `:${check.port}` : ""}{check.path || ""}
                    </td>
                    <td className="px-4 py-4 text-slate-200">{formatPercent(check.uptime_24h)}</td>
                    <td className="px-4 py-4">
                      <div className="text-slate-100">{formatLatency(check.last_response_ms)}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        status code {check.last_status_code || "n/a"}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div className="min-w-[12rem]">
                        <StatusStrip history={check.history} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">No service checks attached.</div>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
          <div className="mb-5 flex items-center gap-3">
            <ShieldAlert className="text-danger" size={18} />
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Incidents</p>
              <h2 className="mt-2 text-2xl font-bold">Recent incident log</h2>
            </div>
          </div>
          <div className="space-y-4">
            {server.recent_incidents.length ? (
              server.recent_incidents.map((incident) => (
                <div key={incident.id} className="rounded-3xl border border-white/8 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{incident.title}</p>
                    <StatusBadge status={incident.status === "resolved" ? "online" : "offline"} />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{incident.description}</p>
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">{formatDate(incident.started_at)}</p>
                </div>
              ))
            ) : (
              <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">No incidents recorded yet.</div>
            )}
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
          <div className="mb-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Latest checks</p>
            <h2 className="mt-2 text-2xl font-bold">Recent result entries</h2>
          </div>
          <div className="space-y-3">
            {server.latest_results.length ? (
              server.latest_results.map((result) => (
                <div key={result.id} className="rounded-3xl border border-white/8 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium uppercase tracking-[0.12em] text-slate-200">{result.check_type}</p>
                    <StatusBadge status={result.status} />
                  </div>
                  <div className="mt-2 text-sm text-slate-400">{result.message || "No message"}</div>
                  <div className="mt-3 text-xs text-slate-500">{formatDate(result.checked_at)}</div>
                </div>
              ))
            ) : (
              <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">No check results recorded yet.</div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
