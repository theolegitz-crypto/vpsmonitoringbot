import { useState } from "react";

const initialState = {
  name: "",
  address: "",
  description: "",
  websiteUrl: "",
  tcpPorts: "22",
  sslDomain: "",
  speedTestEnabled: false,
  speedTestIntervalSeconds: "21600",
};

export function AddServerForm({ onSubmit, busy }) {
  const [form, setForm] = useState(initialState);

  function handleChange(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const ports = form.tcpPorts
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item) => Number(item))
      .filter((item) => Number.isFinite(item));

    const serviceChecks = [];

    if (form.websiteUrl.trim()) {
      serviceChecks.push({
        name: `${form.name}-http`,
        check_type: "http",
        target: form.websiteUrl.trim(),
        path: "",
        interval_seconds: 60,
        timeout_seconds: 5,
      });
    }

    ports.forEach((port) => {
      serviceChecks.push({
        name: `${form.name}-tcp-${port}`,
        check_type: "tcp",
        target: form.address.trim(),
        port,
        interval_seconds: 60,
        timeout_seconds: 5,
      });
    });

    if (form.sslDomain.trim()) {
      serviceChecks.push({
        name: `${form.name}-ssl`,
        check_type: "ssl",
        target: form.sslDomain.trim(),
        port: 443,
        interval_seconds: 3600,
        timeout_seconds: 5,
      });
    }

    await onSubmit({
      name: form.name.trim(),
      address: form.address.trim(),
      description: form.description.trim(),
      speed_test_enabled: Boolean(form.speedTestEnabled),
      speed_test_interval_seconds: Number(form.speedTestIntervalSeconds),
      service_checks: serviceChecks,
    });

    setForm(initialState);
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-[2rem] border border-white/8 bg-panel/85 p-6 shadow-glow">
      <div className="mb-5">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">New monitor</p>
        <h2 className="mt-2 text-2xl font-bold">Add VPS and checks</h2>
        <p className="mt-2 text-sm text-slate-400">
          This creates one server monitor and optional HTTP, TCP and SSL checks in one step.
        </p>
      </div>

      <div className="grid gap-4">
        <input
          required
          name="name"
          value={form.name}
          onChange={handleChange}
          placeholder="Name, for example vps-germany-1"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <input
          required
          name="address"
          value={form.address}
          onChange={handleChange}
          placeholder="IP or domain, for example 203.0.113.10 or vps.example.com"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          placeholder="Description, for example production app server in Frankfurt"
          rows="3"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <input
          name="websiteUrl"
          value={form.websiteUrl}
          onChange={handleChange}
          placeholder="Website URL for HTTP check, for example https://example.com"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <input
          name="tcpPorts"
          value={form.tcpPorts}
          onChange={handleChange}
          placeholder="TCP ports, comma separated, for example 22,443,5432"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <input
          name="sslDomain"
          value={form.sslDomain}
          onChange={handleChange}
          placeholder="SSL domain, for example example.com"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
        <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
          <input
            type="checkbox"
            name="speedTestEnabled"
            checked={form.speedTestEnabled}
            onChange={handleChange}
            className="h-4 w-4 rounded border-white/20 bg-slate-950/30 text-accent focus:ring-accent"
          />
          <span>Enable scheduled speed tests</span>
        </label>
        <input
          type="number"
          min="300"
          step="60"
          name="speedTestIntervalSeconds"
          value={form.speedTestIntervalSeconds}
          onChange={handleChange}
          placeholder="Speed test interval in seconds, for example 21600"
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
        />
      </div>

      <div className="mt-4 rounded-2xl bg-white/5 p-4 text-xs leading-6 text-slate-400">
        Created automatically:
        <br />
        - server availability monitor
        <br />
        - one HTTP check if website URL is filled
        <br />
        - one TCP check per listed port
        <br />
        - one SSL check if SSL domain is filled
        <br />
        - optional scheduled speed tests if enabled and an agent is connected
        <br />
        <br />
        Tip: raw TCP checks go directly to the server address. Add port 80 or 443 only if that exact IP or hostname really accepts direct connections on those ports.
      </div>

      <button
        type="submit"
        disabled={busy}
        className="mt-5 w-full rounded-full bg-accent px-5 py-3 font-semibold text-slate-950 transition hover:bg-accent/90 disabled:opacity-60"
      >
        {busy ? "Creating..." : "Create monitor"}
      </button>
    </form>
  );
}
