import { useState } from "react";
import { Bell, Lock, User } from "lucide-react";
import { Button, Input, PageHeader, Panel } from "../components/ui";
import { useAppDispatch, useAppSelector } from "../store";
import { logout } from "../store/authSlice";

export default function SettingsPage() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email] = useState(user?.email || "");
  const [budgetAlerts, setBudgetAlerts] = useState(true);
  const [goalAlerts, setGoalAlerts] = useState(true);
  const [weeklyDigest, setWeeklyDigest] = useState(false);
  const [savedNote, setSavedNote] = useState("");

  const saveProfile = () => {
    setSavedNote("Profile preferences saved on this device. Account update API coming soon.");
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader
        title="Settings"
        subtitle="Manage your profile, notifications, and account preferences"
      />

      <Panel>
        <div className="mb-4 flex items-center gap-2">
          <User className="h-4 w-4 text-moss" />
          <h2 className="text-lg font-bold text-ink">Profile</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <Input label="Email" value={email} disabled />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" onClick={saveProfile}>
            Save changes
          </Button>
        </div>
        {savedNote ? <p className="mt-3 text-sm text-muted">{savedNote}</p> : null}
      </Panel>

      <Panel>
        <div className="mb-4 flex items-center gap-2">
          <Bell className="h-4 w-4 text-moss" />
          <h2 className="text-lg font-bold text-ink">Notifications</h2>
        </div>
        <ul className="space-y-3">
          {[
            {
              label: "Budget alerts",
              desc: "Get notified when a category is near or over budget",
              value: budgetAlerts,
              set: setBudgetAlerts,
            },
            {
              label: "Goal updates",
              desc: "Track progress reminders for active savings goals",
              value: goalAlerts,
              set: setGoalAlerts,
            },
            {
              label: "Weekly digest",
              desc: "Receive a weekly summary of income, spending, and savings",
              value: weeklyDigest,
              set: setWeeklyDigest,
            },
          ].map((item) => (
            <li
              key={item.label}
              className="flex items-center justify-between gap-4 rounded-xl border border-line bg-sand/40 px-4 py-3"
            >
              <div>
                <p className="text-sm font-semibold text-ink">{item.label}</p>
                <p className="text-xs text-muted">{item.desc}</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={item.value}
                onClick={() => item.set(!item.value)}
                className={`relative h-6 w-11 shrink-0 rounded-full transition ${
                  item.value ? "bg-moss" : "bg-stone"
                }`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
                    item.value ? "left-5" : "left-0.5"
                  }`}
                />
              </button>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel>
        <div className="mb-4 flex items-center gap-2">
          <Lock className="h-4 w-4 text-moss" />
          <h2 className="text-lg font-bold text-ink">Account</h2>
        </div>
        <p className="text-sm text-muted">
          Signed in as <span className="font-semibold text-ink">{user?.email}</span>
        </p>
        <Button
          type="button"
          variant="danger"
          className="mt-4"
          onClick={() => dispatch(logout())}
        >
          Sign out
        </Button>
      </Panel>
    </div>
  );
}
