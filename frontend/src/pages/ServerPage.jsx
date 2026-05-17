import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, BellOff, BellRing } from "lucide-react";

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

      <section className="rounded-[2.5rem] border border-white/8 bg-panel/80 p-8 shadow-glow">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white">
              <ArrowLeft size={16} />
              Back to overview
            </Link>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <h1 className="text-4xl font-bold">{server.name}</h1>
              <StatusBadge status={server.status} />
            </div>
            <p className="mt-3 text-slate-400">{server.address}</p>
            <p className="mt-4 max-w-2xl text-slate-300">{server.description || "No description provided."}</p>
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

        <div className="mt-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 24h</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_24h)}</p>
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
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Muted until</p>
            <p className="mt-2 text-sm font-medium text-slate-200">{server.muted_until ? formatDate(server.muted_until) : "Active"}</p>
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 7d</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_7d)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime 30d</p>
            <p className="mt-2 text-2xl font-semibold">{formatPercent(server.uptime_30d)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Jitter</p>
            <p className="mt-2 text-2xl font-semibold">{formatLatency(server.last_jitter_ms)}</p>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/8 bg-panel/80 p-6 shadow-glow">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Status timeline</p>
            <h2 className="mt-2 text-2xl font-bold">Recent check history</h2>
          </div>
          <p className="text-sm text-slate-400">{server.history.length} samples</p>
        </div>
        <StatusStrip history={server.history} />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <MetricChart data={server.latency_series} dataKey="latency" color="#45f0d1" label="Latency graph" />
        <MetricChart data={server.packet_loss_series} dataKey="packetloss" color="#f9a94b" label="Packet loss graph" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="rounded-[2rem] border border-white/8 bg-panel/80 p-6 shadow-glow">
          <div className="mb-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Checks</p>
            <h2 className="mt-2 text-2xl font-bold">Attached services</h2>
          </div>
          <div className="space-y-4">
            {server.services.length ? (
              server.services.map((check) => (
                <div key={check.id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{check.name}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        {check.check_type} {check.target}{check.port ? `:${check.port}` : ""}
                      </p>
                    </div>
                    <StatusBadge status={check.status} />
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-slate-300">
                    <div>Response: {formatLatency(check.last_response_ms)}</div>
                    <div>Status code: {check.last_status_code || "n/a"}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl bg-white/5 p-4 text-sm text-slate-400">No service checks attached.</div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-[2rem] border border-white/8 bg-panel/80 p-6 shadow-glow">
            <div className="mb-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Incidents</p>
              <h2 className="mt-2 text-2xl font-bold">Recent incident log</h2>
            </div>
            <div className="space-y-4">
              {server.recent_incidents.length ? (
                server.recent_incidents.map((incident) => (
                  <div key={incident.id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{incident.title}</p>
                      <StatusBadge status={incident.status === "resolved" ? "online" : "offline"} />
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{incident.description}</p>
                    <p className="mt-3 text-xs uppercase tracking-[0.2em] text-slate-500">{formatDate(incident.started_at)}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl bg-white/5 p-4 text-sm text-slate-400">No incidents recorded yet.</div>
              )}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/8 bg-panel/80 p-6 shadow-glow">
            <div className="mb-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Alert feed</p>
              <h2 className="mt-2 text-2xl font-bold">Last alert events</h2>
            </div>
            <div className="space-y-3">
              {server.recent_alerts.length ? (
                server.recent_alerts.map((event) => (
                  <div key={event.id} className="rounded-2xl bg-white/5 p-4">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <p className="font-medium uppercase tracking-[0.16em] text-slate-300">{event.event_type}</p>
                      <p className="text-slate-500">{formatDate(event.created_at)}</p>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{event.message}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl bg-white/5 p-4 text-sm text-slate-400">No alert events yet.</div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
