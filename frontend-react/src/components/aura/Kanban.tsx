import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Money } from "@/components/aura/primitives";
import { KanbanSquare, Rows3 } from "lucide-react";

export function ViewToggle({
  view,
  onChange,
}: {
  view: "table" | "kanban";
  onChange: (v: "table" | "kanban") => void;
}) {
  const item = (v: "table" | "kanban", label: string, Icon: typeof Rows3) => (
    <button
      key={v}
      onClick={() => onChange(v)}
      aria-pressed={view === v}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
        view === v
          ? "bg-card text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      <Icon className="size-3.5" /> {label}
    </button>
  );
  return (
    <div className="inline-flex rounded-lg border border-border bg-secondary p-0.5">
      {item("table", "Table", Rows3)}
      {item("kanban", "Kanban", KanbanSquare)}
    </div>
  );
}

export type KanbanColumn<T> = {
  key: string;
  title: string;
  items: T[];
  focus?: boolean;
};

export function KanbanBoard<T>({
  columns,
  renderCard,
  total,
}: {
  columns: KanbanColumn<T>[];
  renderCard: (item: T) => ReactNode;
  total: (items: T[]) => number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number>();

  useEffect(() => {
    const measure = () => {
      const el = ref.current;
      if (!el) return;
      const top = el.getBoundingClientRect().top;
      setHeight(Math.max(320, window.innerHeight - top - 24));
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [columns]);

  return (
    <div ref={ref} className="overflow-x-auto pb-2" style={{ height }}>
      <div className="flex h-full min-w-max items-stretch gap-3">
        {columns.map((col) => (
          <div key={col.key} className="flex w-[292px] shrink-0 flex-col">
            <div
              className={cn(
                "flex items-baseline justify-between rounded-t-xl border border-b-0 bg-card px-3 py-2.5",
                col.focus ? "border-ember" : "border-border",
              )}
            >
              <div className="flex items-center gap-2">
                <span className="label-caps">{col.title}</span>
                <span className="num rounded-md bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                  {col.items.length}
                </span>
              </div>
              <Money value={total(col.items)} className="text-[11px] text-muted-foreground" />
            </div>
            <div
              className={cn(
                "dot-grid flex-1 space-y-2 overflow-y-auto rounded-b-xl border p-2",
                col.focus ? "border-ember" : "border-border",
              )}
            >
              {col.items.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-[11px] text-muted-foreground">
                  Nothing here
                </div>
              ) : (
                col.items.map((item, i) => <div key={i}>{renderCard(item)}</div>)
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
