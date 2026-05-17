import { useState } from "react";
import { LockKeyhole, Radar } from "lucide-react";


export function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      await onLogin({ username, password });
    } catch (submitError) {
      setError(submitError.message || "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-[2rem] border border-white/8 bg-panel/92 p-8 shadow-glow">
        <div className="flex items-center gap-4">
          <div className="rounded-full bg-accent/20 p-4 text-accent">
            <Radar size={24} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">SwagMonitor</p>
            <h1 className="mt-1 text-3xl font-bold">Вход в панель</h1>
          </div>
        </div>

        <p className="mt-5 text-sm text-slate-400">
          Войди под учётной записью администратора или другого пользователя, которому выдали доступ.
        </p>

        {error ? (
          <div className="mt-5 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100">
            {error}
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Логин</label>
            <input
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
              placeholder="admin"
            />
          </div>

          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Пароль</label>
            <input
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
              placeholder="Введите пароль"
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="inline-flex w-full items-center justify-center gap-3 rounded-full bg-accent px-5 py-3 font-semibold text-slate-950 transition hover:bg-accent/90 disabled:opacity-60"
          >
            <LockKeyhole size={18} />
            {busy ? "Входим..." : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}

