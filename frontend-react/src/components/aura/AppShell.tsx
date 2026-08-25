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
  LogOut,
  ClipboardList,
} from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useSession } from "@/components/aura/SessionProvider";

/** `match` is for a nav item that owns more of the app than it links to.
 *  Documents links at its Paperwork tab but stays lit on the Library one,
 *  and without this it would go dark the moment you switched tabs - the
 *  active test is a prefix match on `to`, which the sibling tab fails.
 *  Contacts never needed it because it spends two nav items on two tabs. */
type NavItem = {
  to: string;
  label: string;
  icon: typeof Home;
  founder?: boolean;
  match?: string;
  /** Which reach this link needs. Absent means every session gets it. */
  needs?: "jobs" | "deals" | "settings";
};

// `needs` marks a link the server would refuse for some sessions. A crew
// member holds no permission on Job or Deal at all (T7.1), so a nav full of
// links that answer 403 is worse than a shorter nav - and My work is the door
// they do have. Decided by auraos.api.session_scope rather than by a role name
// read in the browser.
const primaryNav: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/my-work", label: "My work", icon: ClipboardList },
  { to: "/deals", label: "Deals", icon: Handshake, needs: "deals" },
  { to: "/quotations", label: "Quotations", icon: FileSpreadsheet, needs: "deals" },
  { to: "/jobs", label: "Jobs", icon: Clapperboard, needs: "jobs" },
  // Points at the Paperwork tab rather than a bare /documents, the way
  // contactsNav points at a tab rather than a bare /contacts. Paperwork is
  // first because it is the half people open daily.
  {
    to: "/documents/paperwork",
    label: "Documents",
    icon: FileText,
    match: "/documents",
    needs: "jobs",
  },
  { to: "/finance", label: "Finance", icon: Wallet, needs: "jobs" },
];

const contactsNav: NavItem[] = [
  { to: "/contacts/companies", label: "Companies", icon: Building2 },
  { to: "/contacts/people", label: "People", icon: Users },
];

// Settings is readable only by the founder, so a producer never sees the link.
// The server refuses the data either way - this only keeps the nav honest.
const footNav: NavItem[] = [
  { to: "/expense", label: "Quick expense", icon: Receipt, needs: "jobs" },
  // No longer founder-only: T3.5 put the managed lists here, and a producer
  // manages deal sources on this page while the margin floor stays out of
  // reach. The server decides, and the page itself gates the founder half.
  { to: "/settings", label: "Settings", icon: Settings, needs: "settings" },
];

function NavLink({ item }: { item: NavItem }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const prefix = item.match ?? item.to;
  const active = item.to === "/" ? pathname === "/" : pathname.startsWith(prefix);
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      // The open section, said rather than only drawn (#136). Until this
      // existed the current section was carried by background colour alone:
      // visible to anyone looking at the screen and to nobody using it by
      // ear. The condition is the one above - `match` already knows which
      // section owns the page, so this exposes information the component had
      // rather than computing any.
      //
      // A spec asserting it is the second beneficiary and not the reason.
      // The class it replaced could not be asserted honestly: the inactive
      // branch below carries `hover:bg-secondary/70`, which contains the
      // substring `bg-secondary`, so a regex for the lit class matched a dark
      // item and the one test written for #66's regression could not fail.
      aria-current={active ? "page" : undefined}
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
  wide = false,
}: {
  children: ReactNode;
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  /**
   * Let the page use every pixel, instead of the 1296px default.
   *
   * For the screens whose content is genuinely two-dimensional - a board, the
   * quote editor's cost table, bank reconciliation's two facing columns.
   * Atlassian's grid reserves the fluid case for "Kanban boards, whiteboards"
   * and warns to use it sparingly, "because at very large viewports, text
   * lines can become too long". This prop is that "sparingly".
   */
  wide?: boolean;
}) {
  const session = useSession();

  /** Whether this session is offered a link at all. */
  const reachable = (item: NavItem) => {
    if (item.founder && !session.isFounder) return false;
    if (item.needs === "jobs") return session.scope.can_read_jobs;
    if (item.needs === "deals") return session.scope.can_read_deals;
    if (item.needs === "settings") return session.scope.can_read_settings;
    return true;
  };

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
              {primaryNav.filter(reachable).map((i) => (
                <NavLink key={i.to} item={i} />
              ))}
            </div>
            {/* Contacts rides on the deal reach: a crew member has no client
                list to read, and the section header would otherwise sit above
                nothing. */}
            {session.scope.can_read_deals ? (
              <div className="space-y-0.5">
                <div className="label-caps px-2.5 pb-1.5">Contacts</div>
                {contactsNav.map((i) => (
                  <NavLink key={i.to} item={i} />
                ))}
              </div>
            ) : null}
            {footNav.filter(reachable).length > 0 ? (
              <div className="space-y-0.5">
                <div className="label-caps px-2.5 pb-1.5">Studio</div>
                {footNav.filter(reachable).map((i) => (
                  <NavLink key={i.to} item={i} />
                ))}
              </div>
            ) : null}
          </nav>

          <div className="border-t border-border p-3">
            <div className="flex items-center gap-2.5 rounded-lg px-1.5 py-1.5">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-ember-soft text-xs font-semibold text-ember">
                {session.initials}
              </div>
              <div className="min-w-0 flex-1 leading-tight">
                <div className="truncate text-sm font-medium">{session.userName}</div>
                <div className="label-caps">{session.roleLabel}</div>
              </div>
              <button
                type="button"
                onClick={session.logout}
                title="Log out"
                aria-label="Log out"
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <LogOut className="size-4" strokeWidth={1.75} />
              </button>
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

          {/* 1296px is Atlassian's published fixed-wide maximum, which their
              grid names as "the default for most experiences". At the app's
              12px chrome that is ~210 characters a line, down from ~375 on a
              wide monitor - still long, but no longer a line the eye loses its
              place in on the way back. */}
          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6">
            <div className={cn("mx-auto w-full", wide ? "max-w-none" : "max-w-[1296px]")}>
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
