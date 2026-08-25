import { useEffect, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export type FieldDef = {
  name: string;
  label: string;
  type?: "text" | "number" | "select" | "textarea";
  options?: string[];
  placeholder?: string;
  required?: boolean;
  span?: 1 | 2;
  suffix?: string;
};

export function FormDialog({
  open,
  title,
  subtitle,
  fields,
  initial,
  submitLabel = "Create",
  onClose,
  onSubmit,
}: {
  open: boolean;
  title: string;
  subtitle?: ReactNode;
  fields: FieldDef[];
  initial?: Record<string, string>;
  submitLabel?: string;
  onClose: () => void;
  onSubmit: (values: Record<string, string>) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    const base: Record<string, string> = {};
    for (const f of fields) {
      base[f.name] = initial?.[f.name] ?? (f.type === "select" ? (f.options?.[0] ?? "") : "");
    }
    setValues(base);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const missing = fields.some((f) => f.required && !values[f.name]?.trim());

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (missing) return;
          onSubmit(values);
        }}
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

        <div className="grid gap-4 px-5 py-5 sm:grid-cols-2">
          {fields.map((f) => (
            <label key={f.name} className={cn("block", f.span === 2 ? "sm:col-span-2" : undefined)}>
              <span className="label-caps">
                {f.label}
                {f.required ? <span className="text-ember"> *</span> : null}
              </span>
              {f.type === "select" ? (
                <select
                  value={values[f.name] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm outline-none focus:border-border-strong"
                >
                  {(f.options ?? []).map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : f.type === "textarea" ? (
                <textarea
                  rows={3}
                  value={values[f.name] ?? ""}
                  placeholder={f.placeholder}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                  className="mt-1.5 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm outline-none focus:border-border-strong"
                />
              ) : (
                <span className="relative mt-1.5 block">
                  <input
                    type={f.type === "number" ? "number" : "text"}
                    value={values[f.name] ?? ""}
                    placeholder={f.placeholder}
                    onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                    className={cn(
                      "w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm outline-none focus:border-border-strong",
                      f.type === "number" ? "num pr-9 text-right" : undefined,
                    )}
                  />
                  {f.suffix ? (
                    <span className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-muted-foreground">
                      {f.suffix}
                    </span>
                  ) : null}
                </span>
              )}
            </label>
          ))}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-border px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={missing}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            {submitLabel}
          </button>
        </footer>
      </form>
    </div>
  );
}
