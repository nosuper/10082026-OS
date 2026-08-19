import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { vnd } from "@/lib/format";

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

/** The pill's own colours, so a control that has to *look* like a pill does
 * not hand-copy the class string and drift from it. */
export function pillToneClass(tone: string | undefined) {
  return pillTones[tone ?? "neutral"] ?? pillTones["neutral"];
}

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

export function Th({
  children,
  className,
}: {
  children?: ReactNode;
  className?: string | undefined;
}) {
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

/**
 * One text input, so a field on a dialog and a field on a form are the same
 * field. Exported because the deal-stage dialogs need it and a second copy is
 * how two inputs come to disagree about their own border.
 */
export const inputClass =
  "w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong";

/**
 * A dialog. Escape closes it, the backdrop closes it, and the footer is the
 * caller's - the shell should not have opinions about what the buttons say.
 */
export function Modal({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-card shadow-lg"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-base font-semibold tracking-tight">{title}</h2>
            {subtitle ? (
              <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
          >
            <X className="size-4" />
          </button>
        </header>
        {children}
        <footer className="flex items-center justify-end gap-2 border-t border-border px-5 py-4">
          {footer}
        </footer>
      </div>
    </div>
  );
}
