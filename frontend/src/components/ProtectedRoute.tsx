import { Navigate, Outlet } from "react-router-dom";
import { useAppSelector } from "../store";

export default function ProtectedRoute() {
  const status = useAppSelector((s) => s.auth.status);

  if (status === "idle" || status === "loading") {
    return (
      <div className="auth-bg grid min-h-screen place-items-center">
        <div className="text-center">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-moss text-lg font-bold text-black">
            F
          </div>
          <p className="text-lg text-muted">Loading FinSight…</p>
        </div>
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
