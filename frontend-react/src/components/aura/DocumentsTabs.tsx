// The two halves of Documents, and the reason they are two.
//
// Paperwork is transactional: a template is filled from a job's own records
// and the result is a document that belongs to that job. The Library is
// knowledge: an SOP is read, edited in place, and generates nothing. Same
// roof because that is where somebody looks for either; separate lists
// because merging them would mean one screen answering two questions with
// one set of columns.
//
// Route tabs rather than in-page state, which is what ContactsTabs and
// FinanceTabs already do here.
//
// A document does not yet get a URL of its own - the Library opens one in a
// window, the way the Paperwork tab opens a paper - so "send me the link to
// that SOP" still means linking the tab. Worth its own ticket rather than a
// route tree nobody can build-verify while the box is busy.

import { Link } from "@tanstack/react-router";
import { BookOpen, FileText, FolderOpen } from "lucide-react";

export function DocumentsTabs() {
  const tabs = [
    { to: "/documents/paperwork", label: "Paperwork", icon: FileText },
    { to: "/documents/library", label: "Library", icon: BookOpen },
    // Files is the third question under this roof (#28): not "fill a
    // template" and not "read an SOP", but "which deal was that brief on".
    { to: "/documents/files", label: "Files", icon: FolderOpen },
  ] as const;

  return (
    <nav className="inline-flex items-center gap-1 rounded-xl border border-border bg-card p-1">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <Link
            key={tab.to}
            to={tab.to}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-secondary data-[status=active]:font-medium data-[status=active]:text-foreground"
          >
            <Icon className="size-3.5 shrink-0" strokeWidth={1.75} aria-hidden="true" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
