import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, BellOff, BellRing, Pencil, ShieldAlert, Trash2 } from "lucide-react";

import { api } from "../api/client";
import { MetricChart } from "../components/MetricChart";
import { ServerSettingsForm } from "../components/ServerSettingsForm";
import { StatusBadge } from "../components/StatusBadge";
import { StatusStrip } from "../components/StatusStrip";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { formatBytes, formatDate, formatDuration, formatLatency, formatPercent } from "../lib/format";


function formatMegabytes(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return formatBytes(value * 1024 * 1024);
}


function formatGigabytes(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return formatBytes(value * 1024 * 1024 * 1024);
}


function formatSpeed(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return `${Number(value).toFixed(1)} Mbps`;
}


export function ServerPage() {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [server, setServer] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastClientRefreshAt, setLastClientRefreshAt] = useState(null);
  const isEditing = searchParams.get("edit") === "1";

  async function loadServer({ silent = false } = {}) {
    try {
      if (silent) {
        setRefreshing(true);
      }
      setError("");
      const data = await api.server(serverId);
      setServer(data);
      setLastClientRefreshAt(new Date().toISOString());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadServer();
  }, [serverId]);

  useAutoRefresh(
    async () => {
      await loadServer({ silent: true });
    },
    15000,
    [serverId],
  );

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

  async function handleSaveSettings(payload) {
    if (!server) {
      return;
    }
    setBusy(true);
    try {
      await api.updateServer(server.id, payload);
      await loadServer();
      setSearchParams({}, { replace: true });
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteServer() {
    if (!server) {
      return;
    }

    const confirmed = window.confirm(`Delete server "${server.name}" and all attached checks?`);
    if (!confirmed) {
      return;
    }

    setBusy(true);
    try {
      await api.deleteServer(server.id);
      navigate("/");
    } catch (deleteError) {
      setError(deleteError.message);
      setBusy(false);
    }
  }

  async function handleRunSpeedTest() {
    if (!server) {
      return;
    }
    setBusy(true);
    try {
      await api.runSpeedTest(server.id);
      await loadServer();
    } catch (runError) {
      setError(runError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCollectMetrics() {
    if (!server) {
      return;
    }
    setBusy(true);
    try {
      await api.collectServerMetrics(server.id);
      await loadServer();
    } catch (collectError) {
      setError(collectError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleShowLatestSpeedTest() {
    if (!server) {
      return;
    }
    setBusy(true);
    try {
      await loadServer({ silent: true });
    } catch (refreshError) {
      setError(refreshError.message);
    } finally {
      setBusy(false);
    }
  }

  if (!server) {
    return <div className="py-24 text-center text-slate-300">{error || "Loading server..."}</div>;
  }

  const latestAgentMetric = server.latest_system_metric || server.latest_agent_metric;
  const latestSpeedTest = server.latest_speed_test;
  const speedHistory = server.speed_test_history || [];

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
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setSearchParams({ edit: "1" }, { replace: true })}
              disabled={busy}
              className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium transition hover:bg-white/10 disabled:opacity-60"
            >
              <Pencil size={16} />
              Edit server
            </button>
            <button
              type="button"
              onClick={handleMuteToggle}
              disabled={busy}
              className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium transition hover:bg-white/10 disabled:opacity-60"
            >
              {server.muted_until ? <BellRing size={16} /> : <BellOff size={16} />}
              {server.muted_until ? "Unmute alerts" : "Mute for 2 hours"}
            </button>
            <button
              type="button"
              onClick={handleCollectMetrics}
              disabled={busy || !server.ssh_enabled}
              className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium transition hover:bg-white/10 disabled:opacity-60"
            >
              Collect metrics now
            </button>
            <button
              type="button"
              onClick={handleRunSpeedTest}
              disabled={busy || !server.ssh_enabled}
              className="inline-flex items-center gap-3 rounded-full border border-accent/30 bg-accent/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-accent/20 disabled:opacity-60"
            >
              Run speed test over SSH
            </button>
            <button
              type="button"
              onClick={handleDeleteServer}
              disabled={busy}
              className="inline-flex items-center gap-3 rounded-full border border-danger/30 bg-danger/10 px-5 py-3 text-sm font-medium text-red-100 transition hover:bg-danger/20 disabled:opacity-60"
            >
              <Trash2 size={16} />
              Delete server
            </button>
          </div>
        </div>

        <div className="mt-5 rounded-3xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-300">
          <div>Auto refresh: every 15 seconds</div>
          <div className="mt-1">Last UI update: {lastClientRefreshAt ? formatDate(lastClientRefreshAt) : "just now"}</div>
          <div className="mt-1">{refreshing ? "Refreshing..." : "Waiting for next refresh"}</div>
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

        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">SSH metrics</p>
            <p className="mt-2 text-sm font-medium text-slate-200">{server.ssh_enabled ? "Enabled" : "Disabled"}</p>
            <p className="mt-2 text-xs text-slate-500">{server.ssh_username ? `${server.ssh_username}@${server.ssh_host || server.address}:${server.ssh_port}` : "Credentials are not configured yet"}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Last SSH snapshot</p>
            <p className="mt-2 text-sm font-medium text-slate-200">{formatDate(server.last_ssh_metrics_at)}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Diagnostics stored</p>
            <p className="mt-2 text-2xl font-semibold">{server.recent_diagnostics.length}</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Docker collection</p>
            <p className="mt-2 text-2xl font-semibold">{server.ssh_collect_docker ? "On" : "Off"}</p>
            <p className="mt-2 text-sm text-slate-400">{server.current_containers.length} containers in the latest snapshot</p>
          </div>
          <div className="rounded-3xl bg-white/5 p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Speed test schedule</p>
            <p className="mt-2 text-2xl font-semibold">
              {server.speed_test_enabled ? formatDuration(server.speed_test_interval_seconds) : "Disabled"}
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Last queued: {formatDate(server.last_speed_test_requested_at)}
            </p>
          </div>
        </div>
      </section>

      {isEditing ? (
        <ServerSettingsForm
          key={`${server.id}-${server.updated_at || "initial"}`}
          server={server}
          busy={busy}
          onSubmit={handleSaveSettings}
          onCancel={() => setSearchParams({}, { replace: true })}
        />
      ) : null}

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Availability</p>
            <h2 className="mt-2 text-2xl font-bold">Server timeline</h2>
          </div>
          <p className="text-sm text-slate-400">Green OK, yellow degraded, red down, gray no data</p>
        </div>
        <StatusStrip history={server.history} maxVisible={48} compact={false} />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <MetricChart data={server.latency_series} dataKey="latency" color="#45f0d1" label="Latency over time" />
        <MetricChart data={server.packet_loss_series} dataKey="packetloss" color="#f9a94b" label="Packet loss over time" />
      </section>

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Speed test</p>
            <h2 className="mt-2 text-2xl font-bold">Server bandwidth check</h2>
            <p className="mt-2 text-sm text-slate-400">Runs over SSH on the server itself, not in the browser, so it measures the VPS directly.</p>
            <p className="mt-2 text-sm text-slate-500">
              Schedule: {server.speed_test_enabled ? `enabled every ${formatDuration(server.speed_test_interval_seconds)}` : "disabled"}.
            </p>
            <p className="mt-2 text-sm text-slate-500">
              Requires `speedtest` or `speedtest-cli` to be already installed on the VPS.
            </p>
            {!server.ssh_enabled ? (
              <p className="mt-2 text-sm text-amber-200">
                SSH is currently disabled for this server, so queueing is blocked until you add SSH credentials.
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleShowLatestSpeedTest}
              disabled={busy}
              className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/10 disabled:opacity-60"
            >
              Show latest result
            </button>
            <button
              type="button"
              onClick={handleRunSpeedTest}
              disabled={busy || !server.ssh_enabled}
              className="inline-flex items-center gap-3 rounded-full border border-accent/30 bg-accent/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-accent/20 disabled:opacity-60"
            >
              Queue over SSH
            </button>
          </div>
        </div>

        {latestSpeedTest ? (
          <>
            <div className="rounded-3xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-300">
              Status: <span className="font-medium text-white">{latestSpeedTest.status}</span>
              <span className="ml-3">Requested: {formatDate(latestSpeedTest.created_at)}</span>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Download</p>
                <p className="mt-2 text-2xl font-semibold">{formatSpeed(latestSpeedTest.download_mbps)}</p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Upload</p>
                <p className="mt-2 text-2xl font-semibold">{formatSpeed(latestSpeedTest.upload_mbps)}</p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Ping</p>
                <p className="mt-2 text-2xl font-semibold">{formatLatency(latestSpeedTest.ping_ms)}</p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Provider</p>
                <p className="mt-2 text-sm font-medium text-slate-200">{latestSpeedTest.provider_name || "n/a"}</p>
                <p className="mt-2 text-xs text-slate-500">{latestSpeedTest.provider_location || "n/a"}</p>
              </div>
            </div>
            <div className="mt-4 rounded-3xl bg-white/5 p-4 text-sm text-slate-300">
              <div>External IP: {latestSpeedTest.external_ip || "n/a"}</div>
              <div className="mt-2">Started: {formatDate(latestSpeedTest.started_at)}</div>
              <div className="mt-2">Completed: {formatDate(latestSpeedTest.completed_at)}</div>
              {latestSpeedTest.error ? <div className="mt-2 text-red-200">Error: {latestSpeedTest.error}</div> : null}
            </div>
          </>
        ) : (
          <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">
            Speed test has not been run yet. Queue one to measure download, upload and latency directly from the VPS over SSH.
          </div>
        )}

        <div className="mt-6">
          <div className="mb-3">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">History</p>
            <h3 className="mt-2 text-xl font-semibold">Recent speed tests</h3>
          </div>
          {speedHistory.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-[760px] w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-white/8 text-left text-xs uppercase tracking-[0.18em] text-slate-400">
                    <th className="px-4 py-3 font-medium">Requested</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Download</th>
                    <th className="px-4 py-3 font-medium">Upload</th>
                    <th className="px-4 py-3 font-medium">Ping</th>
                    <th className="px-4 py-3 font-medium">Provider</th>
                  </tr>
                </thead>
                <tbody>
                  {speedHistory.map((item) => (
                    <tr key={item.id} className="border-b border-white/6 last:border-b-0">
                      <td className="px-4 py-4 text-slate-200">{formatDate(item.completed_at || item.started_at || item.created_at)}</td>
                      <td className="px-4 py-4">
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-200">
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-200">{formatSpeed(item.download_mbps)}</td>
                      <td className="px-4 py-4 text-slate-200">{formatSpeed(item.upload_mbps)}</td>
                      <td className="px-4 py-4 text-slate-200">{formatLatency(item.ping_ms)}</td>
                      <td className="px-4 py-4 text-slate-300">
                        <div>{item.provider_name || "n/a"}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.provider_location || "n/a"}</div>
                        {item.error ? <div className="mt-1 text-xs text-red-200">{item.error}</div> : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">
              No previous speed tests stored yet.
            </div>
          )}
        </div>
      </section>

      <section className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">System metrics</p>
          <h2 className="mt-2 text-2xl font-bold">Latest VPS snapshot over SSH</h2>
          <p className="mt-2 text-sm text-slate-400">CPU, memory, disk, load average, uptime and cumulative network counters collected without any agent process on the node.</p>
        </div>

        {latestAgentMetric ? (
          <>
            <div className="rounded-3xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-300">
              Snapshot recorded at {formatDate(latestAgentMetric.recorded_at)}
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">CPU</p>
                <p className="mt-2 text-2xl font-semibold">{formatPercent(latestAgentMetric.cpu_percent)}</p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">RAM</p>
                <p className="mt-2 text-2xl font-semibold">{formatPercent(latestAgentMetric.memory_percent)}</p>
                <p className="mt-2 text-sm text-slate-400">
                  {formatMegabytes(latestAgentMetric.memory_used_mb)} / {formatMegabytes(latestAgentMetric.memory_total_mb)}
                </p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Disk</p>
                <p className="mt-2 text-2xl font-semibold">{formatPercent(latestAgentMetric.disk_percent)}</p>
                <p className="mt-2 text-sm text-slate-400">
                  {formatGigabytes(latestAgentMetric.disk_used_gb)} / {formatGigabytes(latestAgentMetric.disk_total_gb)}
                </p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Load average</p>
                <p className="mt-2 text-2xl font-semibold">
                  {[latestAgentMetric.load_1, latestAgentMetric.load_5, latestAgentMetric.load_15]
                    .map((item) => (item === null || item === undefined ? "n/a" : item.toFixed(2)))
                    .join(" / ")}
                </p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Network RX/TX</p>
                <p className="mt-2 text-sm font-medium text-slate-200">
                  RX {formatBytes(latestAgentMetric.net_rx_bytes)}
                </p>
                <p className="mt-2 text-sm font-medium text-slate-200">
                  TX {formatBytes(latestAgentMetric.net_tx_bytes)}
                </p>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Uptime</p>
                <p className="mt-2 text-2xl font-semibold">{formatDuration(latestAgentMetric.uptime_seconds)}</p>
                <p className="mt-2 text-sm text-slate-400">Swap {formatPercent(latestAgentMetric.swap_percent)}</p>
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">
            No SSH metrics have been collected yet. Enable SSH on this server, add login and password, then run "Collect metrics now".
          </div>
        )}
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
                      <div className="w-[15rem]">
                        <StatusStrip history={check.history} maxVisible={24} compact align="end" />
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

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
        <div className="mb-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Containers</p>
          <h2 className="mt-2 text-2xl font-bold">Latest Docker snapshot over SSH</h2>
          <p className="mt-2 text-sm text-slate-400">Current container state, health, restart count and resource usage collected from Docker commands on the VPS.</p>
        </div>

          {server.current_containers.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-[760px] w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-white/8 text-left text-xs uppercase tracking-[0.18em] text-slate-400">
                    <th className="px-4 py-3 font-medium">Container</th>
                    <th className="px-4 py-3 font-medium">State</th>
                    <th className="px-4 py-3 font-medium">Health</th>
                    <th className="px-4 py-3 font-medium">Restarts</th>
                    <th className="px-4 py-3 font-medium">CPU</th>
                    <th className="px-4 py-3 font-medium">Memory</th>
                  </tr>
                </thead>
                <tbody>
                  {server.current_containers.map((container) => (
                    <tr key={container.id} className="border-b border-white/6 last:border-b-0">
                      <td className="px-4 py-4">
                        <div className="font-medium text-slate-100">{container.name}</div>
                        <div className="mt-1 text-xs text-slate-500">{container.image || container.container_id.slice(0, 12)}</div>
                      </td>
                      <td className="px-4 py-4 text-slate-200">{container.state || container.status || "n/a"}</td>
                      <td className="px-4 py-4 text-slate-200">{container.health_status || "n/a"}</td>
                      <td className="px-4 py-4 text-slate-200">{container.restart_count ?? "n/a"}</td>
                      <td className="px-4 py-4 text-slate-200">{formatPercent(container.cpu_percent)}</td>
                      <td className="px-4 py-4 text-slate-200">
                        {formatPercent(container.memory_percent)}
                        <div className="mt-1 text-xs text-slate-500">
                          {formatMegabytes(container.memory_usage_mb)} / {formatMegabytes(container.memory_limit_mb)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">
              No container metrics received yet. If this VPS runs Docker, keep Docker collection enabled and run an SSH metrics snapshot.
            </div>
          )}
        </div>

        <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
          <div className="mb-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Diagnostics</p>
            <h2 className="mt-2 text-2xl font-bold">Recent failure snapshots</h2>
            <p className="mt-2 text-sm text-slate-400">Retry context, DNS lookup and traceroute details captured during recent failures.</p>
          </div>
          <div className="space-y-3">
            {server.recent_diagnostics.length ? (
              server.recent_diagnostics.map((snapshot) => (
                <div key={snapshot.id} className="rounded-3xl border border-white/8 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-100">{snapshot.headline}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                        {snapshot.category} {snapshot.check_type ? `| ${snapshot.check_type}` : ""}
                      </div>
                    </div>
                    <StatusBadge status={snapshot.status || "unknown"} />
                  </div>
                  <div className="mt-3 text-sm text-slate-400">
                    {snapshot.details ? JSON.stringify(snapshot.details).slice(0, 220) : "No details"}
                  </div>
                  <div className="mt-3 text-xs text-slate-500">{formatDate(snapshot.created_at)}</div>
                </div>
              ))
            ) : (
              <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-400">No diagnostic snapshots recorded yet.</div>
            )}
          </div>
        </div>
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
