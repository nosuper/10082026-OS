import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { vnd } from "@/data/fixture";

export function Card({
  children,
  className,
  title,
  subtitle,
  action,
  tone = "light",
}: {
  children?: ReactNode;
  className?: string | undefined;
  title?: string | undefined;
  subtitle?: ReactNode;
  action?: ReactNode;
  tone?: "light" | "ink" | undefined;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border",
        tone === "ink"
          ? "border-transparent bg-primary text-primary-foreground"
          : "border-border bg-card text-card-foreground",
        className,
      )}
    >
      {(title || action) && (
        <header
          className={cn(
            "flex items-start gap-3 border-b px-4 py-3",
            tone === "ink" ? "border-white/10" : "border-border",
          )}
        >
          <div className="min-w-0 flex-1">
            {title ? (
              <h2 className="font-display text-sm font-semibold tracking-tight">{title}</h2>
            ) : null}
            {subtitle ? (
              <div
                className={cn(
                  "mt-0.5 text-xs",
                  tone === "ink" ? "text-primary-foreground/60" : "text-muted-foreground",
                )}
              >
                {subtitle}
              </div>
            ) : null}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Money({
  value,
  className,
  suffix = "₫",
  sign,
}: {
  value: number;
  className?: string | undefined;
  suffix?: string | undefined;
  sign?: boolean | undefined;
}) {
  const prefix = sign && value > 0 ? "+" : "";
  return (
    <span className={cn("num", className)}>
      {prefix}
      {vnd(value)}
      <span className="ml-1 opacity-50">{suffix}</span>
    </span>
  );
}

const pillTones: Record<string, string> = {
  neutral: "bg-secondary text-muted-foreground border-border",
  ink: "bg-primary text-primary-foreground border-transparent",
  ember: "bg-ember-soft text-ember border-transparent",
  outline: "bg-transparent text-foreground border-border-strong",
  positive: "bg-secondary text-positive border-border",
};

export function Pill({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: (keyof typeof pillTones | string) | undefined;
  className?: string | undefined;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap",
        pillTones[tone] ?? pillTones["neutral"],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Stat({
  label,
  value,
  sub,
  alert,
}: {
  label: string;
  value: ReactNode;
  sub?: string | undefined;
  alert?: boolean | undefined;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="label-caps">{label}</div>
      <div
        className={cn(
          "mt-2 num text-xl font-semibold tracking-tight",
          alert ? "text-ember" : "text-foreground",
        )}
      >
        {value}
      </div>
      {sub ? <div className="mt-1 text-xs text-muted-foreground">{sub}</div> : null}
    </div>
  );
}

export function Th({ children, className }: { children?: ReactNode; className?: string | undefined }) {
  return (
    <th className={cn("label-caps px-3 py-2 text-left font-normal whitespace-nowrap", className)}>
      {children}
    </th>
  );
}

export function Td({
  children,
  className,
  colSpan,
}: {
  children?: ReactNode;
  className?: string | undefined;
  colSpan?: number | undefined;
}) {
  return (
    <td colSpan={colSpan} className={cn("px-3 py-2.5 text-sm align-middle", className)}>
      {children}
    </td>
  );
}
