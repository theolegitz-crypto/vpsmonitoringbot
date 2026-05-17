import { useEffect, useState } from "react";
import { ShieldPlus, Users } from "lucide-react";

import { api } from "../api/client";


export function UserAdminCard() {
  const [users, setUsers] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    username: "",
    password: "",
    is_admin: false,
  });

  async function loadUsers() {
    try {
      setError("");
      const data = await api.users();
      setUsers(data);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createUser(form);
      setForm({ username: "", password: "", is_admin: false });
      await loadUsers();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-[2rem] border border-white/8 bg-panel/88 p-6 shadow-glow">
      <div className="mb-4 flex items-center gap-3">
        <Users className="text-accent" size={18} />
        <div>
          <h2 className="text-2xl font-bold">Пользователи</h2>
          <p className="mt-1 text-sm text-slate-400">Добавляй несколько учётных записей для команды.</p>
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-red-100">
          {error}
        </div>
      ) : null}

      <div className="space-y-3">
        {loading ? (
          <div className="rounded-2xl bg-white/5 p-4 text-sm text-slate-400">Загружаю пользователей...</div>
        ) : (
          users.map((user) => (
            <div key={user.id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="font-medium">{user.username}</div>
                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">
                  {user.is_admin ? "admin" : "user"}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <div>
          <label className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Новый логин</label>
          <input
            required
            value={form.username}
            onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
            placeholder="operator"
          />
        </div>

        <div>
          <label className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Пароль</label>
          <input
            required
            type="password"
            value={form.password}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-accent"
            placeholder="Минимум 6 символов"
          />
        </div>

        <label className="flex items-center gap-3 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={form.is_admin}
            onChange={(event) => setForm((current) => ({ ...current, is_admin: event.target.checked }))}
            className="h-4 w-4 rounded border-white/20 bg-white/5"
          />
          Выдать права администратора
        </label>

        <button
          type="submit"
          disabled={busy}
          className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 font-semibold text-slate-950 transition hover:bg-accent/90 disabled:opacity-60"
        >
          <ShieldPlus size={16} />
          {busy ? "Создаю..." : "Создать пользователя"}
        </button>
      </form>
    </div>
  );
}
