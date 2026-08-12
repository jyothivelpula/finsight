import { useMemo, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import { clearError, login, register } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";

type Mode = "signin" | "register";

export default function Auth() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { status, error } = useAppSelector((s) => s.auth);

  const initialMode: Mode = location.pathname.includes("register") ? "register" : "signin";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [googleNote, setGoogleNote] = useState("");

  const isRegister = mode === "register";
  const loading = status === "loading";

  const title = useMemo(
    () => (isRegister ? "Create account" : "Sign in"),
    [isRegister],
  );

  if (status === "authenticated") return <Navigate to="/app" replace />;

  const switchMode = (next: Mode) => {
    setMode(next);
    setGoogleNote("");
    dispatch(clearError());
    navigate(next === "register" ? "/register" : "/login", { replace: true });
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    dispatch(clearError());
    if (isRegister) {
      dispatch(register({ email, full_name: fullName, password }));
    } else {
      dispatch(login({ email, password }));
    }
  };

  return (
    <div className="auth-bg flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="mb-8 flex flex-col items-center text-center animate-rise">
        <BrandLogo className="mb-5" imgClassName="h-12 w-auto max-w-[240px]" />
        <h1 className="text-3xl font-semibold tracking-tight text-ink md:text-4xl">
          Welcome to FinSight
        </h1>
        <p className="mt-2 text-sm text-muted md:text-base">
          Your private financial command centre.
        </p>
      </div>

      <div className="card-shadow w-full max-w-[420px] animate-rise rounded-2xl border border-line bg-card p-5 sm:p-6">
        <div className="mb-6 grid grid-cols-2 rounded-xl bg-sand p-1">
          <button
            type="button"
            onClick={() => switchMode("signin")}
            className={`rounded-lg px-3 py-2.5 text-sm font-medium transition ${
              !isRegister ? "bg-moss text-white shadow-lg shadow-moss/20" : "text-muted hover:text-white"
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => switchMode("register")}
            className={`rounded-lg px-3 py-2.5 text-sm font-medium transition ${
              isRegister ? "bg-moss text-white shadow-lg shadow-moss/20" : "text-muted hover:text-white"
            }`}
          >
            Create account
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {isRegister ? (
            <label className="block space-y-2">
              <span className="text-sm font-medium text-ink">Full name</span>
              <input
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-xl border border-transparent bg-[#eef3ff] px-3.5 py-3 text-sm text-[#171819] outline-none transition placeholder:text-slate-500 focus:border-moss/60 focus:ring-2 focus:ring-moss/20"
                placeholder="Your name"
              />
            </label>
          ) : null}

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-transparent bg-[#eef3ff] px-3.5 py-3 text-sm text-[#171819] outline-none transition placeholder:text-slate-500 focus:border-moss/60 focus:ring-2 focus:ring-moss/20"
              placeholder="you@email.com"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink">Password</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-transparent bg-[#eef3ff] px-3.5 py-3 text-sm text-[#171819] outline-none transition placeholder:text-slate-500 focus:border-moss/60 focus:ring-2 focus:ring-moss/20"
              placeholder="••••••••"
            />
          </label>

          {error ? <p className="text-sm text-danger">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-moss py-3 text-sm font-semibold text-white transition hover:bg-leaf disabled:opacity-60"
          >
            {loading ? "Please wait…" : title}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-line" />
          <span className="text-[11px] font-semibold tracking-[0.18em] text-muted">OR</span>
          <div className="h-px flex-1 bg-line" />
        </div>

        <button
          type="button"
          onClick={() =>
            setGoogleNote("Google sign-in will be available soon. Use email for now.")
          }
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-line bg-transparent py-3 text-sm font-medium text-ink transition hover:bg-sand"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
            <path
              fill="#EA4335"
              d="M12 10.2v3.6h5.1c-.2 1.2-1.5 3.6-5.1 3.6-3.1 0-5.6-2.5-5.6-5.6S8.9 6.2 12 6.2c1.8 0 3 .7 3.7 1.4l2.5-2.4C16.8 3.8 14.6 2.8 12 2.8 6.9 2.8 2.8 6.9 2.8 12S6.9 21.2 12 21.2c5.5 0 9.1-3.9 9.1-9.3 0-.6-.1-1.1-.2-1.7H12z"
            />
          </svg>
          Continue with Google
        </button>
        {googleNote ? <p className="mt-3 text-center text-xs text-muted">{googleNote}</p> : null}
      </div>
    </div>
  );
}
