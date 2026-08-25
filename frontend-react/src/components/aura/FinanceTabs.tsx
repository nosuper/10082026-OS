import { Link } from "@tanstack/react-router";

const tabs = [
  { to: "/finance", label: "Dashboard", exact: true },
  { to: "/finance/accounts", label: "Accounts" },
  { to: "/finance/bank", label: "Bank" },
  { to: "/finance/income", label: "Income" },
  { to: "/finance/expenses", label: "Expenses" },
  { to: "/finance/receivables", label: "Receivables" },
  { to: "/finance/reports", label: "Reports" },
  { to: "/finance/forecast", label: "Forecast" },
] as const;

export function FinanceTabs() {
  return (
    <nav className="flex flex-wrap items-center gap-1 rounded-xl border border-border bg-card p-1">
      {tabs.map((t) => (
        <Link
          key={t.to}
          to={t.to}
          activeOptions={{ exact: "exact" in t ? t.exact : false }}
          className="rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-secondary data-[status=active]:font-medium data-[status=active]:text-foreground"
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}

/** Simple horizontal proportion bar used across the finance pages. */
export function Bar({
  value,
  max,
  tone = "ink",
}: {
  value: number;
  max: number;
  tone?: "ink" | "ember" | "positive" | "muted";
}) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  const bg =
    tone === "ember"
      ? "bg-ember"
      : tone === "positive"
        ? "bg-positive"
        : tone === "muted"
          ? "bg-border-strong"
          : "bg-primary";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
      <div className={`h-full rounded-full ${bg}`} style={{ width: `${pct}%` }} />
    </div>
  );
}
