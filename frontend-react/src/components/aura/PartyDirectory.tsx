// What the two Contacts screens share: the same two doctypes, the same role
// filter, the same paperwork rule and one form that edits either side of the
// book. Only src/routes/contacts.companies.tsx and contacts.people.tsx import
// this file.
//
// The directory is Party Company and Party Contact read through
// lib/queries.ts, and written back with frappe.client.insert /
// frappe.client.save - the same calls the Vue screen has been making in
// production. There is no bespoke endpoint behind any of it.

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Building2, Search, Users, X } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import { Pill } from "@/components/aura/primitives";
import { ErrorState, Loading } from "@/components/aura/states";
import { VN_BANKS } from "@/data/banks";
import type { FrappeError, ListFilters } from "@/lib/frappe";
import { listsOf, useDoc, useList, useMethodMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

export type PartyDoctype = "Party Company" | "Party Contact";

export type CompanyRow = {
  name: string;
  company_name: string | null;
  tax_code: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  bank_account_number: string | null;
};

export type PersonRow = {
  name: string;
  full_name: string | null;
  company: string | null;
  phone: string | null;
  email: string | null;
  id_number: string | null;
  tax_code: string | null;
  bank_account_number: string | null;
};

type RoleTag = { party_role: string };

type PartyDoc = Record<string, unknown> & { name: string; role_tags?: RoleTag[] };

// -- paperwork -------------------------------------------------------------
//
// What a contract needs before it can be generated without gap markers in it.
// A record missing any of these prints holes, so the holes are named in the
// directory instead of on the paper.

const COMPANY_DOCS: Array<[keyof CompanyRow, string]> = [
  ["tax_code", "tax code"],
  ["address", "address"],
  ["bank_account_number", "bank"],
];

const PERSON_DOCS: Array<[keyof PersonRow, string]> = [
  ["id_number", "CCCD"],
  ["tax_code", "tax code"],
  ["bank_account_number", "bank"],
];

function missingFrom<T>(row: T, spec: Array<[keyof T, string]>): string[] {
  return spec.filter(([field]) => !row[field]).map(([, label]) => label);
}

export function companyPaperwork(row: CompanyRow): string[] {
  return missingFrom(row, COMPANY_DOCS);
}

export function personPaperwork(row: PersonRow): string[] {
  return missingFrom(row, PERSON_DOCS);
}

/** The sentence the column reports, and the text search matches against. */
export function paperworkLabel(missing: string[]): string {
  return missing.length ? `missing ${missing.join(", ")}` : "complete";
}

/** The paperwork cell: a marker to spot down the column, and the real gaps. */
export function Paperwork({ missing }: { missing: string[] }) {
  if (!missing.length) return <Pill tone="positive">Complete</Pill>;
  return (
    <span className="flex min-w-0 items-center gap-1.5">
      <Pill tone="ember" className="shrink-0">
        Missing
      </Pill>
      <span className="truncate text-xs text-muted-foreground">{missing.join(", ")}</span>
    </span>
  );
}

// -- filtering -------------------------------------------------------------

/**
 * Role chips filter on the Party Role Tag child table, which the server does
 * for us. Doing it here in the browser would only ever be right for the rows
 * already loaded.
 *
 * Spread into the list query rather than returned as a value: with
 * exactOptionalPropertyTypes an absent filter has to be an absent key, not an
 * `undefined` one.
 */
export function roleTagFilter(role: string): { filters?: ListFilters } {
  return role ? { filters: [["Party Role Tag", "party_role", "=", role]] } : {};
}

export function usePartyRoles(): UseQueryResult<{ name: string }[], FrappeError> {
  return useList<{ name: string }>({
    doctype: "Party Role",
    fields: ["name"],
    orderBy: "name asc",
  });
}

/**
 * Companies as pickable options. The People screen needs them for the company
 * column and the form needs them for its picker, and because both ask the
 * same question with the same arguments they share one request.
 */
export function useCompanyOptions(): UseQueryResult<
  { name: string; company_name: string | null }[],
  FrappeError
> {
  return useList<{ name: string; company_name: string | null }>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
    orderBy: "company_name asc",
  });
}

/** Lower-cased text of everything on a row, so search matches what is shown. */
export function haystack(...parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" ").toLowerCase();
}

export function ContactsTabs() {
  const tabs = [
    { to: "/contacts/companies", label: "Companies", icon: Building2 },
    { to: "/contacts/people", label: "People", icon: Users },
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

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-2">
      <Search className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
      />
    </label>
  );
}

export function RoleChips({
  roles,
  value,
  onChange,
}: {
  roles: string[];
  value: string;
  onChange: (role: string) => void;
}) {
  const options = [
    { label: "All roles", value: "" },
    ...roles.map((r) => ({ label: r, value: r })),
  ];
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {options.map((option) => (
        <button
          key={option.value || "all"}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-lg border px-2.5 py-1.5 text-xs transition-colors",
            value === option.value
              ? "border-transparent bg-primary font-medium text-primary-foreground"
              : "border-border bg-card text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

// -- the form --------------------------------------------------------------

type FieldDef = {
  name: string;
  label: string;
  type?: "text" | "email" | "date" | "textarea";
  required?: boolean;
  wide?: boolean;
  /** Digits only, so it may wear the mono face. Never a name or an address. */
  numeric?: boolean;
};

const COMPANY_FIELDS: FieldDef[] = [
  { name: "company_name", label: "Company name", required: true, wide: true },
  // Suggested from the name by auraos.api.suggest_short_code and editable
  // afterwards. Not required: a client with no contract yet does not need
  // one, and generation asks when it is missing rather than inventing it.
  { name: "short_code", label: "Short code" },
  { name: "tax_code", label: "Tax code", numeric: true },
  { name: "phone", label: "Phone", numeric: true },
  { name: "email", label: "Email", type: "email" },
  { name: "website", label: "Website" },
  { name: "address", label: "Address", type: "textarea", wide: true },
];

const CONTACT_FIELDS: FieldDef[] = [
  { name: "full_name", label: "Full name", required: true },
  { name: "phone", label: "Phone / Zalo", required: true, numeric: true },
  { name: "email", label: "Email", type: "email" },
];

// Revealed by the Freelancer role tag: what a freelancer contract prints.
const FREELANCER_FIELDS: FieldDef[] = [
  { name: "id_number", label: "ID number (CCCD)", numeric: true },
  { name: "date_of_birth", label: "Date of birth", type: "date" },
  { name: "tax_code", label: "Personal tax code", numeric: true },
  { name: "permanent_address", label: "Permanent address", type: "textarea" },
  { name: "contact_address", label: "Contact address", type: "textarea" },
];

const BANK_FIELDS: FieldDef[] = [
  { name: "bank_account_number", label: "Bank account number", numeric: true },
  { name: "bank_account_name", label: "Bank account name" },
];

// The server refuses this tag on a company, so the form does not offer it.
const ROLES_NOT_FOR_COMPANIES = ["Freelancer"];

function fieldsFor(doctype: PartyDoctype): FieldDef[] {
  return doctype === "Party Contact" ? CONTACT_FIELDS : COMPANY_FIELDS;
}

/** Every fieldname the form owns, so nothing else on the doc is overwritten. */
function editableNames(doctype: PartyDoctype): string[] {
  const names = [
    ...fieldsFor(doctype).map((f) => f.name),
    ...BANK_FIELDS.map((f) => f.name),
    "bank_name",
    "notes",
  ];
  if (doctype === "Party Contact") {
    names.push("company", ...FREELANCER_FIELDS.map((f) => f.name));
  }
  return [...new Set(names)];
}

function formFromDoc(doc: PartyDoc, doctype: PartyDoctype): Record<string, string> {
  const form: Record<string, string> = {};
  for (const key of editableNames(doctype)) {
    const value = doc[key];
    form[key] = value === null || value === undefined ? "" : String(value);
  }
  return form;
}

/** Blank means "not filled in", which the server stores as null, not "". */
function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function Label({ htmlFor, children }: { htmlFor: string; children: ReactNode }) {
  return (
    <label className="label-caps block" htmlFor={htmlFor}>
      {children}
    </label>
  );
}

const inputClass =
  "mt-1.5 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm outline-none focus:border-border-strong";

function Field({
  field,
  value,
  onChange,
}: {
  field: FieldDef;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = `party-${field.name}`;
  return (
    <div className={field.wide ? "sm:col-span-2" : undefined}>
      <Label htmlFor={id}>
        {field.label}
        {field.required ? <span className="text-ember"> *</span> : null}
      </Label>
      {field.type === "textarea" ? (
        <textarea
          id={id}
          rows={2}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={inputClass}
        />
      ) : (
        <input
          id={id}
          type={field.type === "date" ? "date" : field.type === "email" ? "email" : "text"}
          value={value}
          required={field.required}
          onChange={(event) => onChange(event.target.value)}
          className={cn(inputClass, field.numeric || field.type === "date" ? "num" : undefined)}
        />
      )}
    </div>
  );
}

/**
 * Create or edit one party. `name` null means create.
 *
 * An existing doc is read whole and the edits are laid over the server's copy
 * on save, so `modified` makes the round trip and Frappe can still refuse a
 * write that would clobber someone else's.
 */
export function PartyFormDialog({
  open,
  doctype,
  name,
  onClose,
  onSaved,
}: {
  open: boolean;
  doctype: PartyDoctype;
  name: string | null;
  onClose: () => void;
  onSaved: (savedName: string) => void;
}) {
  const isContact = doctype === "Party Contact";
  const [form, setForm] = useState<Record<string, string>>({});
  const [roles, setRoles] = useState<string[]>([]);
  const serverDoc = useRef<PartyDoc | null>(null);

  const doc = useDoc<PartyDoc>(doctype, name ?? undefined, {
    enabled: open && Boolean(name),
  });
  const allRoles = usePartyRoles();
  const companies = useCompanyOptions();

  const invalidate = [listsOf("Party Company"), listsOf("Party Contact"), ["doc", doctype]];

  const saved = (result: { name?: string } | null) => {
    onSaved(result?.name ?? name ?? "");
    onClose();
  };

  const insert = useMethodMutation<{ name?: string }, { doc: Record<string, unknown> }>(
    "frappe.client.insert",
    { invalidate, onSuccess: saved },
  );
  const update = useMethodMutation<{ name?: string }, { doc: Record<string, unknown> }>(
    "frappe.client.save",
    { invalidate, onSuccess: saved },
  );

  // Opening is the reset: a dialog reopened on another record must not show
  // the last one's half-typed values.
  useEffect(() => {
    if (!open) return;
    serverDoc.current = null;
    setForm({});
    setRoles([]);
    insert.reset();
    update.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, name, doctype]);

  useEffect(() => {
    if (!open || !name) return;
    const loaded = doc.data;
    if (!loaded || serverDoc.current) return;
    serverDoc.current = loaded;
    setForm(formFromDoc(loaded, doctype));
    setRoles((loaded.role_tags ?? []).map((tag) => tag.party_role));
  }, [open, name, doctype, doc.data]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const offeredRoles = (allRoles.data ?? [])
    .map((role) => role.name)
    .filter((role) => isContact || !ROLES_NOT_FOR_COMPANIES.includes(role));
  const showFreelancer = isContact && roles.includes("Freelancer");
  const fields = fieldsFor(doctype);
  const value = (key: string) => form[key] ?? "";
  const set = (key: string) => (next: string) => setForm((prev) => ({ ...prev, [key]: next }));

  const pending = insert.isPending || update.isPending;
  const error = insert.error ?? update.error;
  const loadingDoc = Boolean(name) && doc.isPending;
  const required = fields.filter((f) => f.required);
  const incomplete = required.some((f) => !value(f.name).trim());

  function submit(event: FormEvent) {
    event.preventDefault();
    if (incomplete || pending) return;

    const payload: Record<string, unknown> = { ...(serverDoc.current ?? {}), doctype };
    // Only the fields this form owns; the freelancer block is written even
    // when hidden, because unchecking Freelancer should not silently wipe the
    // paperwork somebody already typed.
    for (const key of editableNames(doctype)) {
      if (key in form) payload[key] = nullable(value(key));
    }
    payload["role_tags"] = roles.map((role) => ({
      doctype: "Party Role Tag",
      party_role: role,
    }));

    if (name) update.mutate({ doc: payload });
    else insert.mutate({ doc: payload });
  }

  const noun = isContact ? "person" : "company";
  const title = name ? `Edit ${noun}` : `New ${noun}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <button
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <form
        onSubmit={submit}
        className="relative z-10 w-full max-w-2xl rounded-xl border border-border bg-card shadow-lg"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 flex-1">
            <div className="label-caps">{isContact ? "Person" : "Company"}</div>
            <h2 className="mt-0.5 font-display text-base font-semibold tracking-tight">{title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {isContact
                ? "People carry their own paperwork: CCCD, tax code and bank."
                : "Companies hold tax code, address and bank details for contracts."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </header>

        {loadingDoc ? (
          <Loading rows={5} className="px-5 py-6" label="Loading the record" />
        ) : doc.isError ? (
          <ErrorState error={doc.error} onRetry={() => void doc.refetch()} />
        ) : (
          <div className="space-y-5 px-5 py-5">
            <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2">
              {fields.map((field) => (
                <Field
                  key={field.name}
                  field={field}
                  value={value(field.name)}
                  onChange={set(field.name)}
                />
              ))}

              {isContact ? (
                <div className="sm:col-span-2">
                  <Label htmlFor="party-company">Company</Label>
                  <select
                    id="party-company"
                    value={value("company")}
                    onChange={(event) => set("company")(event.target.value)}
                    className={inputClass}
                  >
                    <option value="">No company</option>
                    {(companies.data ?? []).map((company) => (
                      <option key={company.name} value={company.name}>
                        {company.company_name || company.name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            {/* Role tags decide what the rest of the form asks for, so they sit
                above the sections they reveal. */}
            <fieldset className="border-t border-border pt-4">
              <legend className="label-caps">Role tags</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {offeredRoles.map((role) => (
                  <label
                    key={role}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors",
                      roles.includes(role)
                        ? "border-border-strong bg-secondary font-medium"
                        : "border-border bg-background text-muted-foreground",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={roles.includes(role)}
                      onChange={(event) =>
                        setRoles((prev) =>
                          event.target.checked ? [...prev, role] : prev.filter((r) => r !== role),
                        )
                      }
                      className="size-3.5 accent-ember"
                    />
                    {role}
                  </label>
                ))}
                {allRoles.isError ? (
                  <p className="text-xs text-muted-foreground">Roles did not load.</p>
                ) : offeredRoles.length === 0 && !allRoles.isPending ? (
                  <p className="text-xs text-muted-foreground">No roles defined yet.</p>
                ) : null}
              </div>
            </fieldset>

            {showFreelancer ? (
              <fieldset className="border-t border-border pt-4">
                <legend className="label-caps">Freelancer paperwork</legend>
                <p className="mt-1 text-xs text-muted-foreground">
                  Blank fields print as gaps on the contract.
                </p>
                <div className="mt-2 grid gap-x-4 gap-y-3 sm:grid-cols-2">
                  {FREELANCER_FIELDS.map((field) => (
                    <Field
                      key={field.name}
                      field={field}
                      value={value(field.name)}
                      onChange={set(field.name)}
                    />
                  ))}
                </div>
              </fieldset>
            ) : null}

            <fieldset className="border-t border-border pt-4">
              <legend className="label-caps">Bank</legend>
              <div className="mt-2 grid gap-x-4 gap-y-3 sm:grid-cols-2">
                <div>
                  <Label htmlFor="party-bank_name">Bank name</Label>
                  <select
                    id="party-bank_name"
                    value={value("bank_name")}
                    onChange={(event) => set("bank_name")(event.target.value)}
                    className={inputClass}
                  >
                    <option value="">No bank</option>
                    {VN_BANKS.map((bank) => (
                      <option key={bank} value={bank}>
                        {bank}
                      </option>
                    ))}
                  </select>
                </div>
                {BANK_FIELDS.map((field) => (
                  <Field
                    key={field.name}
                    field={field}
                    value={value(field.name)}
                    onChange={set(field.name)}
                  />
                ))}
              </div>
            </fieldset>

            <div className="border-t border-border pt-4">
              <Label htmlFor="party-notes">Notes</Label>
              <textarea
                id="party-notes"
                rows={2}
                value={value("notes")}
                onChange={(event) => set("notes")(event.target.value)}
                className={inputClass}
              />
            </div>

            {error ? <ErrorState error={error} className="px-0 py-2" /> : null}
          </div>
        )}

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
            disabled={incomplete || pending || loadingDoc}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            {pending ? "Saving..." : name ? "Save" : `Create ${noun}`}
          </button>
        </footer>
      </form>
    </div>
  );
}
