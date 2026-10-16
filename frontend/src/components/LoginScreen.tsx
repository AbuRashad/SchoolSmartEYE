import { useState } from "react";
import { LogIn, ShieldCheck } from "lucide-react";
import { useAuth } from "../AuthContext";

export function LoginScreen() {
  const { login, sessionExpired } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-academic px-4 text-white">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-5 rounded-[2rem] border border-white/10 bg-panel px-8 py-10 shadow-panel"
      >
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-cobalt/20 p-3 text-sky">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-mist/60">Campus Command</p>
            <h1 className="text-2xl font-semibold">Sign in</h1>
          </div>
        </div>

        {sessionExpired && !error && (
          <p className="rounded-2xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
            Your session expired. Please sign in again.
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-2xl border border-critical/40 bg-critical/10 px-4 py-3 text-sm text-critical">
            {error}
          </p>
        )}

        <label className="block space-y-1 text-sm text-mist/80">
          Username
          <input
            autoFocus
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-white outline-none focus:border-cobalt"
          />
        </label>
        <label className="block space-y-1 text-sm text-mist/80">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-white outline-none focus:border-cobalt"
          />
        </label>

        <button
          type="submit"
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cobalt px-4 py-2.5 text-sm font-medium text-white transition hover:bg-cobalt/90 disabled:opacity-60"
        >
          <LogIn className="h-4 w-4" />
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
