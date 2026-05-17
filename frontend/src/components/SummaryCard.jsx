export function SummaryCard({ label, value, helper, accent }) {
  return (
    <div className="rounded-3xl border border-white/8 bg-panel/80 p-5 shadow-glow backdrop-blur">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <div className="mt-4 flex items-end justify-between gap-4">
        <p className={`text-4xl font-bold ${accent}`}>{value}</p>
        <p className="max-w-[8rem] text-right text-sm text-slate-400">{helper}</p>
      </div>
    </div>
  );
}

