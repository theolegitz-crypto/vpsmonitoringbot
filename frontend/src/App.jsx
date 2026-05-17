import { useEffect, useState } from "react";
import { Routes, Route, Link } from "react-router-dom";
import { LogOut, Radar } from "lucide-react";

import { api } from "./api/client";
import { LoginPage } from "./components/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ServerPage } from "./pages/ServerPage";

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  async function loadCurrentUser() {
    try {
      const data = await api.me();
      setUser(data);
    } catch (error) {
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }

  useEffect(() => {
    loadCurrentUser();

    function handleUnauthorized() {
      setUser(null);
      setAuthLoading(false);
    }

    window.addEventListener("swagmonitor:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("swagmonitor:unauthorized", handleUnauthorized);
    };
  }, []);

  async function handleLogin(payload) {
    const result = await api.login(payload);
    setUser(result.user);
  }

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">
        Проверяю сессию...
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

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
          <div className="flex items-center gap-3 self-start lg:self-auto">
            <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
              {user.username} {user.is_admin ? "(admin)" : ""}
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
            >
              <LogOut size={16} />
              Выйти
            </button>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<OverviewPage currentUser={user} />} />
          <Route path="/servers/:serverId" element={<ServerPage />} />
        </Routes>
      </div>
    </div>
  );
}
