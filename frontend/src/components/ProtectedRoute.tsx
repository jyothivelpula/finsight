import { Navigate, Outlet } from "react-router-dom";
import BrandLogo from "./BrandLogo";
import { useAppSelector } from "../store";

export default function ProtectedRoute() {
  const status = useAppSelector((s) => s.auth.status);

  if (status === "idle" || status === "loading") {
    return (
      <div className="auth-bg grid min-h-screen place-items-center">
        <div className="text-center">
          <BrandLogo className="mx-auto mb-4" imgClassName="h-10 w-auto max-w-[200px]" />
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
