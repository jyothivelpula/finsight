import { Navigate } from "react-router-dom";
import { useAppSelector } from "../store";

/** Landing redirects into the dark auth experience from the design. */
export default function Landing() {
  const status = useAppSelector((s) => s.auth.status);
  if (status === "authenticated") return <Navigate to="/app" replace />;
  return <Navigate to="/login" replace />;
}
