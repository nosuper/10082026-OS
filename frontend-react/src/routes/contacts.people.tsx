// People, on real data.
//
// The other half of the directory: Party Contact, the company each person
// belongs to, and the paperwork a freelancer contract needs from them. Same
// role filter and same form as contacts.companies.tsx.

import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Mail, Phone, Plus } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import {
  ContactsTabs,
  Paperwork,
  PartyFormDialog,
  RoleChips,
  SearchBox,
  haystack,
  paperworkLabel,
  personPaperwork,
  roleTagFilter,
  useCompanyOptions,
  usePartyRoles,
  type PersonRow,
} from "@/components/aura/PartyDirectory";
import { Card, Td, Th } from "@/components/aura/primitives";
import { QueryStates } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useList } from "@/lib/queries";

export const Route = createFileRoute("/contacts/people")({
  head: () => ({
    meta: [
      { title: "People - AuraOS contacts" },
      {
        name: "description",
        content:
          "Individual contacts with phone, email, role tags, the company they belong to and the paperwork still missing.",
      },
      { property: "og:title", content: "People - AuraOS contacts" },
      {
        property: "og:description",
        content: "Clients, crew and freelancers with their role tags and paperwork gaps.",
      },
    ],
  }),
  component: PeoplePage,
});

type Listed = PersonRow & {
  companyLabel: string;
  missing: string[];
  search: string;
};

function PeoplePage() {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [dialog, setDialog] = useState<{ open: boolean; name: string | null }>({
    open: false,
    name: null,
  });

  const roles = usePartyRoles();
  // Same arguments as the form's own company read, so the two share a request.
  const companies = useCompanyOptions();

  const people = useList<PersonRow>({
    doctype: "Party Contact",
    fields: [
      "name",
      "full_name",
      "company",
      "phone",
      "email",
      "id_number",
      "tax_code",
      "bank_account_number",
    ],
    ...roleTagFilter(role),
    // Qualified on purpose: with a role chip on, the server joins Party Role
    // Tag, which has a `modified` of its own, and a bare "modified desc" comes
    // back as "Column 'modified' in ORDER BY is ambiguous".
    orderBy: "`tabParty Contact`.modified desc",
  });

  const companyName = useMemo(
    () => new Map((companies.data ?? []).map((c) => [c.name, c.company_name ?? c.name])),
    [companies.data],
  );

  const listed: Listed[] = useMemo(
    () =>
      (people.data ?? []).map((row) => {
        const missing = personPaperwork(row);
        const label = paperworkLabel(missing);
        const companyLabel = row.company ? (companyName.get(row.company) ?? row.company) : "";
        return {
          ...row,
          companyLabel,
          missing,
          search: haystack(
            row.name,
            row.full_name,
            companyLabel,
            row.phone,
            row.email,
            row.id_number,
            row.tax_code,
            row.bank_account_number,
            label,
          ),
        };
      }),
    [people.data, companyName],
  );

  const term = query.trim().toLowerCase();
  const rows = term ? listed.filter((row) => row.search.includes(term)) : listed;
  const incomplete = listed.filter((row) => row.missing.length).length;

  const meta = people.isSuccess
    ? [
        countLabel(listed.length, "person", "people"),
        incomplete ? `${incomplete} missing paperwork` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  return (
    <AppShell
      title="People"
      meta={meta}
      actions={
        <button
          type="button"
          onClick={() => setDialog({ open: true, name: null })}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New person
        </button>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <ContactsTabs />
          <SearchBox value={query} onChange={setQuery} placeholder="Search people or company" />
        </div>

        <RoleChips roles={(roles.data ?? []).map((r) => r.name)} value={role} onChange={setRole} />

        <Card
          title="Directory"
          subtitle={people.isSuccess ? countLabel(rows.length, "person", "people") : undefined}
        >
          <QueryStates
            queries={[people, companies]}
            isEmpty={() => rows.length === 0}
            empty={{
              title: "Nothing here yet.",
              detail:
                term || role
                  ? "No person matches this search or role."
                  : "Create the first person with the button above.",
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Name</Th>
                      <Th>Company</Th>
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
                        <Td className="font-medium">{row.full_name || row.name}</Td>
                        <Td className="text-muted-foreground">{row.companyLabel || "-"}</Td>
                        <Td>
                          <span className="flex items-center gap-1.5 text-muted-foreground">
                            <Phone className="size-3 shrink-0" aria-hidden="true" />
                            <span className="num text-xs">{row.phone || "-"}</span>
                          </span>
                        </Td>
                        <Td>
                          <span className="flex items-center gap-1.5 text-muted-foreground">
                            <Mail className="size-3 shrink-0" aria-hidden="true" />
                            <span className="truncate">{row.email || "-"}</span>
                          </span>
                        </Td>
                        <Td>
                          <Paperwork missing={row.missing} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </QueryStates>
        </Card>
      </div>

      <PartyFormDialog
        open={dialog.open}
        doctype="Party Contact"
        name={dialog.name}
        onClose={() => setDialog({ open: false, name: null })}
        onSaved={() => setDialog({ open: false, name: null })}
      />
    </AppShell>
  );
}
