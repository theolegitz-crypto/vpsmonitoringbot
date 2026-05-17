import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ListChecks, PlusCircle, ServerCog } from "lucide-react";

import { api } from "../api/client";
import { AddServerForm } from "../components/AddServerForm";
import { MonitorTable } from "../components/MonitorTable";
import { SummaryCard } from "../components/SummaryCard";
import { UserAdminCard } from "../components/UserAdminCard";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatDate, formatLatency, formatPercent } from "../lib/format";


function buildMonitorRows(servers) {
  return servers.flatMap((server) => {
    const serverRow = {
      id: `server-${server.id}`,
      kind: "server",
      name: server.name,
      note: server.description || "Main VPS availability monitor",
      typeLabel: "SERVER",
      status: server.status,
      target: server.address,
      uptime24h: server.uptime_24h,
      uptime7d: server.uptime_7d,
      uptime30d: server.uptime_30d,
      currentPrimary: `Ping ${formatLatency(server.last_latency_ms)}`,
      currentSecondary: `Loss ${formatPercent(server.last_packet_loss)} | Jitter ${formatLatency(server.last_jitter_ms)}`,
      history: server.history,
      link: `/servers/${server.id}`,
      runId: server.id,
    };

    const serviceRows = server.services.map((check) => {
      const checkTarget = `${check.target}${check.port ? `:${check.port}` : ""}${check.path || ""}`;
      const currentPrimary =
        check.check_type === "ssl"
          ? `SSL check`
          : `Response ${formatLatency(check.last_response_ms)}`;
      const currentSecondary =
        check.check_type === "http"
          ? `HTTP ${check.last_status_code || "n/a"}`
          : check.check_type === "tcp"
            ? `Port ${check.port || "n/a"}`
            : check.last_error || "Certificate status";

      return {
        id: `service-${check.id}`,
        kind: "service",
        name: check.name,
        note: `Attached to ${server.name}`,
        typeLabel: check.check_type.toUpperCase(),
        status: check.status,
        target: checkTarget,
        uptime24h: check.uptime_24h,
        uptime7d: check.uptime_7d,
        uptime30d: check.uptime_30d,
        currentPrimary,
        currentSecondary,
        history: check.history,
        link: `/servers/${server.id}`,
        runId: check.id,
      };
    });

    return [serverRow, ...serviceRows];
  });
}


export function OverviewPage({ currentUser }) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastClientRefreshAt, setLastClientRefreshAt] = useState(null);

  async function loadOverview({ silent = false } = {}) {
    try {
      if (silent) {
        setRefreshing(true);
      }
      setError("");
      const data = await api.overview();
      setOverview(data);
      setLastClientRefreshAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  useAutoRefresh(
    async () => {
      await loadOverview({ silent: true });
    },
    15000,
    [],
  );

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

  async function handleRefreshService(serviceId) {
    try {
      await api.runServiceCheck(serviceId);
      await loadOverview();
    } catch (runError) {
      setError(runError.message);
    }
  }

  async function handleDeleteServer(serverId, serverName) {
    const confirmed = window.confirm(`Delete server "${serverName}" and all attached checks?`);
    if (!confirmed) {
      return;
    }

    try {
      await api.deleteServer(serverId);
      await loadOverview();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  const rows = useMemo(() => buildMonitorRows(overview?.servers || []), [overview]);

  if (loading) {
    return <div className="py-24 text-center text-slate-300">Loading monitoring data...</div>;
  }

  if (!overview) {
    return <div className="py-24 text-center text-danger">{error || "Failed to load overview."}</div>;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-7 shadow-glow">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.26em] text-accent">Overview</p>
            <h1 className="mt-3 text-3xl font-bold md:text-4xl">VPS and service monitoring in a clear monitor list.</h1>
            <p className="mt-3 text-slate-400">
              One row per server or service, uptime percentages, recent history blocks, and quick actions for manual checks.
            </p>
          </div>
          <div className="rounded-3xl border border-white/8 bg-white/5 px-5 py-4 text-sm text-slate-300">
            <div>Generated: {formatDate(overview.generated_at)}</div>
            <div className="mt-2">Auto refresh: every 15 seconds</div>
            <div className="mt-2">Last UI update: {lastClientRefreshAt ? formatDate(lastClientRefreshAt) : "just now"}</div>
            <div className="mt-2">Rows in monitor table: {rows.length}</div>
            <div className="mt-2">Incidents stored: {overview.recent_incidents.length}</div>
            <div className="mt-2">{refreshing ? "Refreshing..." : "Waiting for next refresh"}</div>
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-3xl border border-danger/30 bg-danger/10 px-5 py-4 text-sm text-red-100">{error}</div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Servers" value={overview.summary.total} helper="Configured VPS nodes" accent="text-ink" />
        <SummaryCard label="Online" value={overview.summary.online} helper="Healthy primary monitors" accent="text-success" />
        <SummaryCard label="Degraded" value={overview.summary.degraded} helper="Latency, packet loss or SSL warnings" accent="text-warning" />
        <SummaryCard label="Offline" value={overview.summary.offline} helper="Host or service not reachable" accent="text-danger" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.55fr_0.8fr]">
        <div className="space-y-6">
          <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
            <div className="mb-5 flex items-center gap-3">
              <ListChecks className="text-accent" size={18} />
              <div>
                <h2 className="text-2xl font-bold">Monitor list</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Server rows are followed by service rows. The table refreshes automatically, and the history column shows only the latest blocks so the layout stays stable.
                </p>
              </div>
            </div>

            {rows.length ? (
              <MonitorTable
                rows={rows}
                onRunServer={handleRefreshServer}
                onRunService={handleRefreshService}
                onDeleteServer={handleDeleteServer}
              />
            ) : (
              <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-6 text-slate-400">
                No monitors yet. Use the form on the right to create the first VPS and its checks.
              </div>
            )}
          </div>

          <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
            <div className="mb-4 flex items-center gap-3">
              <ServerCog className="text-accentWarm" size={18} />
              <div>
                <h2 className="text-2xl font-bold">How to use this screen</h2>
                <p className="mt-1 text-sm text-slate-400">A short operator-oriented workflow instead of a decorative landing page.</p>
              </div>
            </div>
            <div className="grid gap-3 text-sm text-slate-300">
              <div>1. Add a VPS with name and IP or domain.</div>
              <div>2. Optionally attach website, TCP ports and SSL checks in the same form.</div>
              <div>3. Wait for the first monitoring loop. The page refreshes itself every 15 seconds.</div>
              <div>4. Open a server page to inspect latency, packet loss, incidents and service rows in detail.</div>
              <div>5. Read the history strip: green is OK, yellow is degraded, red is down, gray is no data.</div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <AddServerForm onSubmit={handleCreateServer} busy={creating} />

          <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
            <div className="mb-4 flex items-center gap-3">
              <AlertTriangle className="text-danger" size={18} />
              <div>
                <h2 className="text-2xl font-bold">Recent incidents</h2>
                <p className="mt-1 text-sm text-slate-400">Shows failures and recoveries tracked by the alert engine.</p>
              </div>
            </div>
            <div className="space-y-4">
              {overview.recent_incidents.length ? (
                overview.recent_incidents.map((incident) => (
                  <div key={incident.id} className="rounded-3xl border border-white/8 bg-white/5 p-4">
                    <div className="font-medium text-slate-100">{incident.title}</div>
                    <div className="mt-2 text-sm text-slate-400">{incident.description}</div>
                    <div className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">
                      {formatDate(incident.started_at)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">No incidents recorded yet.</div>
              )}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
            <div className="mb-4 flex items-center gap-3">
              <PlusCircle className="text-accent" size={18} />
              <div>
                <h2 className="text-2xl font-bold">Suggested starter checks</h2>
                <p className="mt-1 text-sm text-slate-400">Good defaults for most personal or small production VPS setups.</p>
              </div>
            </div>
            <div className="grid gap-3 text-sm text-slate-300">
              <div>- ICMP for raw reachability and latency.</div>
              <div>- TCP 22 for SSH access.</div>
              <div>- TCP 80 and 443 for public web reachability.</div>
              <div>- HTTP or HTTPS check for real application response code.</div>
              <div>- SSL check to catch expiring certificates early.</div>
            </div>
          </div>

          {currentUser?.is_admin ? <UserAdminCard /> : null}
        </div>
      </section>
    </div>
  );
}
