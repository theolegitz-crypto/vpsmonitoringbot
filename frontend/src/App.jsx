import { Routes, Route, Link } from "react-router-dom";
import { Radar } from "lucide-react";

import { OverviewPage } from "./pages/OverviewPage";
import { ServerPage } from "./pages/ServerPage";

export default function App() {
  return (
    <div className="grid-pattern min-h-screen text-ink">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col gap-4 rounded-[2rem] border border-white/8 bg-slate-950/55 px-6 py-5 shadow-glow backdrop-blur lg:flex-row lg:items-center lg:justify-between">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="rounded-full bg-accent/20 p-3 text-accent">
              <Radar size={20} />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Monitoring</p>
              <p className="text-xl font-bold">SwagMonitor Control Room</p>
            </div>
          </Link>
          <p className="max-w-xl text-sm text-slate-400">
            A compact operations view for VPS reachability, packet loss, website checks, TCP ports and SSL incidents.
          </p>
        </header>

        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/servers/:serverId" element={<ServerPage />} />
        </Routes>
      </div>
    </div>
  );
}
