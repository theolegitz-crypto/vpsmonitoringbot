import { useEffect, useState } from "react";


function toFormState(server) {
  return {
    name: server.name || "",
    address: server.address || "",
    description: server.description || "",
    latency_warning_ms: String(server.latency_warning_ms ?? 150),
    latency_critical_ms: String(server.latency_critical_ms ?? 400),
    packet_loss_warning: String(server.packet_loss_warning ?? 5),
    packet_loss_critical: String(server.packet_loss_critical ?? 20),
    check_interval_seconds: String(server.check_interval_seconds ?? 60),
    consecutive_alert_threshold: String(server.consecutive_alert_threshold ?? 3),
    speed_test_enabled: Boolean(server.speed_test_enabled),
    speed_test_interval_seconds: String(server.speed_test_interval_seconds ?? 21600),
  };
}


export function ServerSettingsForm({ server, busy, onSubmit, onCancel }) {
  const [form, setForm] = useState(() => toFormState(server));

  useEffect(() => {
    setForm(toFormState(server));
  }, [server.id, server.updated_at]);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    await onSubmit({
      name: form.name.trim(),
      address: form.address.trim(),
      description: form.description.trim() || null,
      latency_warning_ms: Number(form.latency_warning_ms),
      latency_critical_ms: Number(form.latency_critical_ms),
      packet_loss_warning: Number(form.packet_loss_warning),
      packet_loss_critical: Number(form.packet_loss_critical),
      check_interval_seconds: Number(form.check_interval_seconds),
      consecutive_alert_threshold: Number(form.consecutive_alert_threshold),
      speed_test_enabled: Boolean(form.speed_test_enabled),
      speed_test_interval_seconds: Number(form.speed_test_interval_seconds),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-[2rem] border border-white/8 bg-white/5 p-6">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Edit</p>
        <h2 className="mt-2 text-2xl font-bold">Server settings</h2>
        <p className="mt-2 text-sm text-slate-400">
          Update the main server profile and alert thresholds without touching the database manually.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Name</span>
          <input
            required
            name="name"
            value={form.name}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Address</span>
          <input
            required
            name="address"
            value={form.address}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
      </div>

      <label className="mt-4 grid gap-2 text-sm">
        <span className="text-slate-300">Description</span>
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          rows="3"
          className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
      </label>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Latency warning, ms</span>
          <input
            required
            type="number"
            min="1"
            step="1"
            name="latency_warning_ms"
            value={form.latency_warning_ms}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Latency critical, ms</span>
          <input
            required
            type="number"
            min="1"
            step="1"
            name="latency_critical_ms"
            value={form.latency_critical_ms}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Packet loss warning, %</span>
          <input
            required
            type="number"
            min="0"
            max="100"
            step="0.1"
            name="packet_loss_warning"
            value={form.packet_loss_warning}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Packet loss critical, %</span>
          <input
            required
            type="number"
            min="0"
            max="100"
            step="0.1"
            name="packet_loss_critical"
            value={form.packet_loss_critical}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Check interval, seconds</span>
          <input
            required
            type="number"
            min="10"
            step="1"
            name="check_interval_seconds"
            value={form.check_interval_seconds}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Consecutive failures before alert</span>
          <input
            required
            type="number"
            min="1"
            step="1"
            name="consecutive_alert_threshold"
            value={form.consecutive_alert_threshold}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm text-slate-200">
          <input
            type="checkbox"
            name="speed_test_enabled"
            checked={form.speed_test_enabled}
            onChange={handleChange}
            className="h-4 w-4 rounded border-white/20 bg-slate-950/30 text-accent focus:ring-accent"
          />
          <span>Enable scheduled speed tests</span>
        </label>
        <label className="grid gap-2 text-sm">
          <span className="text-slate-300">Speed test interval, seconds</span>
          <input
            required
            type="number"
            min="300"
            step="60"
            name="speed_test_interval_seconds"
            value={form.speed_test_interval_seconds}
            onChange={handleChange}
            className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm outline-none transition focus:border-accent"
          />
        </label>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-accent/90 disabled:opacity-60"
        >
          {busy ? "Saving..." : "Save changes"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm text-slate-200 transition hover:bg-white/10 disabled:opacity-60"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
