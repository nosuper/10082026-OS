import { Link, useRouterState } from "@tanstack/react-router";
import {
  Home,
  Handshake,
  Clapperboard,
  FileText,
  FileSpreadsheet,
  Building2,
  Users,
  Settings,
  Search,
  Command,
  Receipt,
  Wallet,
} from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type NavItem = { to: string; label: string; icon: typeof Home; founder?: boolean };

const primaryNav: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/deals", label: "Deals", icon: Handshake },
  { to: "/quotations", label: "Quotations", icon: FileSpreadsheet },
  { to: "/jobs", label: "Jobs", icon: Clapperboard },
  { to: "/paperwork", label: "Paperwork", icon: FileText },
  { to: "/finance", label: "Finance", icon: Wallet },
];


const contactsNav: NavItem[] = [
  { to: "/contacts/companies", label: "Companies", icon: Building2 },
  { to: "/contacts/people", label: "People", icon: Users },
];

const footNav: NavItem[] = [
  { to: "/expense", label: "Quick expense", icon: Receipt },
  { to: "/settings", label: "Settings", icon: Settings },
];

function NavLink({ item }: { item: NavItem }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
        active
          ? "bg-secondary font-medium text-foreground"
          : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground",
      )}
    >
      <Icon className={cn("size-4 shrink-0", active && "text-ember")} strokeWidth={1.75} />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function AppShell({
  children,
  title,
  meta,
  actions,
}: {
  children: ReactNode;
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background dot-grid">
      <div className="flex min-h-screen">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-border bg-sidebar/90 backdrop-blur lg:flex">
          <div className="flex items-center gap-2.5 px-4 py-5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <span className="font-display text-sm font-bold">A</span>
            </div>
            <div className="leading-tight">
              <div className="font-display text-sm font-semibold">AuraOS</div>
              <div className="label-caps">Production ops</div>
            </div>
          </div>

          <nav className="flex-1 space-y-6 px-2.5 pb-4">
            <div className="space-y-0.5">
              {primaryNav.map((i) => (
                <NavLink key={i.to} item={i} />
              ))}
            </div>
            <div className="space-y-0.5">
              <div className="label-caps px-2.5 pb-1.5">Contacts</div>
              {contactsNav.map((i) => (
                <NavLink key={i.to} item={i} />
              ))}
            </div>
            <div className="space-y-0.5">
              <div className="label-caps px-2.5 pb-1.5">Studio</div>
              {footNav.map((i) => (
                <NavLink key={i.to} item={i} />
              ))}
            </div>
          </nav>

          <div className="border-t border-border p-3">
            <div className="flex items-center gap-2.5 rounded-lg px-1.5 py-1.5">
              <div className="flex size-8 items-center justify-center rounded-full bg-ember-soft text-xs font-semibold text-ember">
                TB
              </div>
              <div className="min-w-0 leading-tight">
                <div className="truncate text-sm font-medium">Trần Quốc Bảo</div>
                <div className="label-caps">Founder</div>
              </div>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur">
            <div className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
              <div className="min-w-0 flex-1">
                <h1 className="truncate font-display text-lg font-semibold">{title}</h1>
                {meta ? <div className="mt-0.5 text-xs text-muted-foreground">{meta}</div> : null}
              </div>
              <div className="hidden items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-muted-foreground md:flex">
                <Search className="size-3.5" strokeWidth={1.75} />
                <span>Quick actions</span>
                <span className="ml-6 flex items-center gap-0.5 rounded border border-border px-1 py-0.5 num text-[10px]">
                  <Command className="size-3" /> K
                </span>
              </div>
              {actions}
            </div>
          </header>

          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
