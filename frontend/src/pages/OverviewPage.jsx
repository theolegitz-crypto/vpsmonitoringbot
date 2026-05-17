import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Server, Signal } from "lucide-react";

import { api } from "../api/client";
import { AddServerForm } from "../components/AddServerForm";
import { ServerCard } from "../components/ServerCard";
import { SummaryCard } from "../components/SummaryCard";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate } from "../lib/format";

export function OverviewPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  async function loadOverview() {
    try {
      setError("");
      const data = await api.overview();
      setOverview(data);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  async function handleCreateServer(payload) {
    setCreating(true);
    try {
      await api.addServer(payload);
      await loadOverview();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleRefreshServer(serverId) {
    try {
      await api.runServerCheck(serverId);
      await loadOverview();
    } catch (runError) {
      setError(runError.message);
    }
  }

  if (loading) {
    return <div className="py-24 text-center text-slate-300">Loading monitoring data...</div>;
  }

  if (!overview) {
    return <div className="py-24 text-center text-danger">{error || "Failed to load overview."}</div>;
  }

  return (
    <div className="space-y-10">
      <section className="rounded-[2.5rem] border border-white/8 bg-panel/75 p-8 shadow-glow backdrop-blur">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-accent">SwagMonitor</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight md:text-6xl">
              Dark ops panel for VPS availability, latency, SSL health and incident history.
            </h1>
            <p className="mt-4 max-w-2xl text-base text-slate-400">
              Track hosts, websites and custom TCP ports in one place with alert-aware status timelines.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm text-slate-400">
            <div className="rounded-3xl bg-white/5 p-4">
              <p>Generated</p>
              <p className="mt-2 font-mono text-slate-100">{formatDate(overview.generated_at)}</p>
            </div>
            <div className="rounded-3xl bg-white/5 p-4">
              <p>Incidents</p>
              <p className="mt-2 font-mono text-slate-100">{overview.recent_incidents.length}</p>
            </div>
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-3xl border border-danger/30 bg-danger/10 px-5 py-4 text-sm text-red-100">{error}</div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Servers" value={overview.summary.total} helper="All monitored VPS targets" accent="text-ink" />
        <SummaryCard label="Online" value={overview.summary.online} helper="Healthy and stable nodes" accent="text-success" />
        <SummaryCard label="Degraded" value={overview.summary.degraded} helper="Latency, loss or SSL warnings" accent="text-warning" />
        <SummaryCard label="Offline" value={overview.summary.offline} helper="Hosts or checks that are failing" accent="text-danger" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="grid gap-6">
          {overview.servers.length ? (
            overview.servers.map((server) => (
              <ServerCard key={server.id} server={server} onRefresh={handleRefreshServer} />
            ))
          ) : (
            <div className="rounded-[2rem] border border-dashed border-white/10 bg-panel/70 p-8 text-slate-400">
              No servers yet. Create the first monitor from the panel on the right.
            </div>
          )}
        </div>

        <div className="space-y-6">
          <AddServerForm onSubmit={handleCreateServer} busy={creating} />

          <div className="rounded-[2rem] border border-white/8 bg-panel/85 p-6 shadow-glow">
            <div className="flex items-center gap-3">
              <AlertTriangle className="text-accentWarm" size={18} />
              <h2 className="text-xl font-bold">Recent incidents</h2>
            </div>
            <div className="mt-5 space-y-4">
              {overview.recent_incidents.length ? (
                overview.recent_incidents.map((incident) => (
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

          <div className="rounded-[2rem] border border-white/8 bg-panel/85 p-6 shadow-glow">
            <div className="mb-4 flex items-center gap-3">
              <Signal className="text-accent" size={18} />
              <h2 className="text-xl font-bold">Legend</h2>
            </div>
            <div className="grid gap-3 text-sm text-slate-300">
              <div className="flex items-center gap-3"><span className="h-3 w-3 rounded-sm bg-success" /> Green means everything is healthy.</div>
              <div className="flex items-center gap-3"><span className="h-3 w-3 rounded-sm bg-danger" /> Red means host or check is unavailable.</div>
              <div className="flex items-center gap-3"><span className="h-3 w-3 rounded-sm bg-warning" /> Yellow means degraded performance or SSL warning.</div>
              <div className="flex items-center gap-3"><span className="h-3 w-3 rounded-sm bg-slate-500" /> Gray means not enough data yet.</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

