// Companies, on real data.
//
// Half of the directory: Party Company read through lib/queries.ts, filtered
// on its Party Role Tag child table by the server, and written back with the
// shared party form. The other half is contacts.people.tsx; the tab is the
// URL, so a reload lands on the side you were reading.

import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Plus, Users } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import {
  ContactsTabs,
  Paperwork,
  PartyFormDialog,
  RoleChips,
  SearchBox,
  companyPaperwork,
  haystack,
  paperworkLabel,
  roleTagFilter,
  usePartyRoles,
  type CompanyRow,
} from "@/components/aura/PartyDirectory";
import { Card, Td, Th } from "@/components/aura/primitives";
import { QueryState } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useList } from "@/lib/queries";

export const Route = createFileRoute("/contacts/companies")({
  head: () => ({
    meta: [
      { title: "Companies - AuraOS contacts" },
      {
        name: "description",
        content:
          "Client, vendor and partner companies with tax codes, contact details and the paperwork a contract still needs.",
      },
      { property: "og:title", content: "Companies - AuraOS contacts" },
      {
        property: "og:description",
        content: "Company directory with role tags, tax codes and paperwork gaps.",
      },
    ],
  }),
  component: CompaniesPage,
});

type Listed = CompanyRow & { missing: string[]; search: string };

function CompaniesPage() {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [dialog, setDialog] = useState<{ open: boolean; name: string | null }>({
    open: false,
    name: null,
  });

  const roles = usePartyRoles();

  // The role chip is part of the request: filtering the child table here in
  // the browser would only ever be right for the rows already loaded.
  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: [
      "name",
      "company_name",
      "tax_code",
      "phone",
      "email",
      "address",
      "bank_account_number",
    ],
    ...roleTagFilter(role),
    // Qualified on purpose: with a role chip on, the server joins Party Role
    // Tag, which has a `modified` of its own, and a bare "modified desc" comes
    // back as "Column 'modified' in ORDER BY is ambiguous".
    orderBy: "`tabParty Company`.modified desc",
  });

  const listed: Listed[] = useMemo(
    () =>
      (companies.data ?? []).map((row) => {
        const missing = companyPaperwork(row);
        const label = paperworkLabel(missing);
        return {
          ...row,
          missing,
          search: haystack(
            row.name,
            row.company_name,
            row.tax_code,
            row.phone,
            row.email,
            row.address,
            row.bank_account_number,
            label,
          ),
        };
      }),
    [companies.data],
  );

  const term = query.trim().toLowerCase();
  const rows = term ? listed.filter((row) => row.search.includes(term)) : listed;
  const incomplete = listed.filter((row) => row.missing.length).length;

  const meta = companies.isSuccess
    ? [
        countLabel(listed.length, "company", "companies"),
        incomplete ? `${incomplete} missing paperwork` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  return (
    <AppShell
      title="Companies"
      meta={meta}
      actions={
        <button
          type="button"
          onClick={() => setDialog({ open: true, name: null })}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New company
        </button>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <ContactsTabs />
          <SearchBox value={query} onChange={setQuery} placeholder="Search companies" />
        </div>

        <RoleChips roles={(roles.data ?? []).map((r) => r.name)} value={role} onChange={setRole} />

        <Card
          title="Directory"
          subtitle={
            companies.isSuccess ? countLabel(rows.length, "company", "companies") : undefined
          }
        >
          <QueryState
            query={companies}
            isEmpty={() => rows.length === 0}
            empty={{
              title: "Nothing here yet.",
              detail:
                term || role
                  ? "No company matches this search or role."
                  : "Create the first company with the button above.",
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Company</Th>
                      <Th>Tax code</Th>
                      <Th>Phone</Th>
                      <Th>Email</Th>
                      <Th>Paperwork</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rows.map((row) => (
                      <tr
                        key={row.name}
                        tabIndex={0}
                        onClick={() => setDialog({ open: true, name: row.name })}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") setDialog({ open: true, name: row.name });
                        }}
                        className="cursor-pointer hover:bg-secondary/50"
                      >
                        <Td>
                          <div className="font-medium">{row.company_name || row.name}</div>
                          {row.address ? (
                            <div className="truncate text-xs text-muted-foreground">
                              {row.address}
                            </div>
                          ) : null}
                        </Td>
                        <Td className="num text-xs text-muted-foreground">{row.tax_code || "-"}</Td>
                        <Td className="num text-xs text-muted-foreground">{row.phone || "-"}</Td>
                        <Td className="text-muted-foreground">{row.email || "-"}</Td>
                        <Td>
                          <Paperwork missing={row.missing} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        {roles.isSuccess && roles.data.length === 0 ? (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Users className="size-3.5" /> No party roles are defined yet, so the role filter is
            empty.
          </p>
        ) : null}
      </div>

      <PartyFormDialog
        open={dialog.open}
        doctype="Party Company"
        name={dialog.name}
        onClose={() => setDialog({ open: false, name: null })}
        onSaved={() => setDialog({ open: false, name: null })}
      />
    </AppShell>
  );
}
