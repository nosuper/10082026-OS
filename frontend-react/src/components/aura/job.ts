// What the job record is made of: the server's own vocabulary, and the shapes
// its endpoints send.
//
// Only the job screen and its three panels read this. It exists because the
// page and the panels have to agree on the same words - a status spelled
// differently on one of them silently stops matching a stored value - and
// because the panels are separate files so the tabs can keep their state.
//
// Every constant here mirrors a server constant, which is the authority:
// STAGES is auraos.auraos.doctype.job.job.STAGES, the collection flow is
// auraos.lib.milestones.STATUS_FLOW, and the money words are
// auraos.lib.settlement.

/** The agreed production flow, in order. The server refuses anything else. */
export const STAGES = [
  "Pre-production",
  "Production",
  "Post-production",
  "Client review",
  "Delivery",
  "Client sign-off",
  "Awaiting payment",
  "Complete",
];

/** What a new job starts with; the stored value on the job wins. */
export const INCLUDED_REVISION_ROUNDS = 2;

/**
 * Where logging a revision sends a job the client has already been shown, and
 * the last stage that still redoes. Mirrors redo_stage_for on the server, which
 * decides it; this only lets the screen warn before the stage moves.
 */
export const REDO_STAGE = "Post-production";
export const LAST_REDOABLE_STAGE = "Delivery";

/**
 * The collection flow, in order. The stored value is English like every other
 * status in the app; the Vietnamese beside it is what the founder and the
 * accountant actually say, so the control shows both.
 */
export const COLLECTION_STATUSES = [
  { value: "Not requested", vi: "chưa yêu cầu" },
  { value: "Requested", vi: "đã yêu cầu KT" },
  { value: "Invoiced", vi: "đã xuất HĐ" },
  { value: "Paid", vi: "đã thanh toán" },
];

export const PAID = "Paid";

/**
 * Statuses whose money is already committed on paper. An invoiced or paid
 * milestone's share is history: it never rebalances itself, because changing
 * its percentage would rewrite an invoice the client already holds.
 */
export const LOCKED_STATUSES = ["Invoiced", "Paid"];

/** Where an expense's money came from. */
export const FROM_ADVANCE = "Advance";
export const FROM_COMPANY = "Company";

/** Which way a float has to move to close. */
export const RETURN = "Return";
export const EVEN = "Even";

// -- what the server sends --

export type JobRevisionRow = {
  name: string;
  round: number | null;
  chargeable: number | null;
  requested_on: string | null;
  logged_by: string | null;
  note: string | null;
};

export type JobPackageRow = {
  name: string;
  title: string | null;
  description: string | null;
  price: number | null;
};

export type JobLinkRow = { name: string; label: string | null; url: string | null };

export type StageChangeRow = {
  name: string;
  from_stage: string | null;
  to_stage: string | null;
  changed_on: string | null;
  changed_by: string | null;
};

/** The whole Job document, as frappe.client.get returns it. */
export type JobDoc = {
  name: string;
  title: string | null;
  stage: string;
  job_owner: string | null;
  files_location: string | null;
  deal: string | null;
  company: string | null;
  contact: string | null;
  included_revision_rounds: number | null;
  revision_rounds: number | null;
  change_order_due: number | null;
  quote_subtotal: number | null;
  quote_mf_amount: number | null;
  quote_vat_amount: number | null;
  quote_total: number | null;
  revisions: JobRevisionRow[];
  packages: JobPackageRow[];
  job_links: JobLinkRow[];
  stage_history: StageChangeRow[];
};

/** One payment milestone, with the lateness verdict already made server-side. */
export type Milestone = {
  name: string | null;
  idx: number | null;
  title: string | null;
  pct: number | null;
  trigger_stage: string | null;
  amount: number | null;
  status: string;
  due_on: string | null;
  requested_on: string | null;
  invoiced_on: string | null;
  paid_on: string | null;
  overdue: boolean;
  days_overdue: number;
};

export type MilestonesPayload = { payment_terms_days: number; milestones: Milestone[] };

export type AdvanceRow = {
  name: string;
  recipient: string | null;
  amount: number | null;
  transferred_on: string | null;
  note: string | null;
};

export type ExpenseRow = {
  name: string;
  spent_on: string | null;
  amount: number | null;
  category: string | null;
  description: string | null;
  paid_by: string | null;
  paid_from: string | null;
  photo: string | null;
  creation: string | null;
};

export type FloatRow = {
  holder: string;
  advanced: number;
  spent: number;
  settled: number;
  amount: number;
  direction: string;
};

export type CategoryRow = { title: string; quoted: number; actual: number; variance: number };

/** auraos.api.job_money: the whole money-out question in one answer. */
export type MoneyPayload = {
  advances: AdvanceRow[];
  expenses: ExpenseRow[];
  floats: FloatRow[];
  categories: CategoryRow[];
  advanced_total: number;
  spent_total: number;
  quoted_total: number;
  /** What this session may do with money, asked of the permissions themselves. */
  may_advance: boolean;
  may_settle: boolean;
};

export type OperatingUser = { name: string; full_name: string | null };

/** frappe.client.set_value, the one write that touches the job itself. */
export type SetValueArgs = {
  doctype: string;
  name: string;
  fieldname: Record<string, string | number>;
};

/**
 * The cache key useDoc reads under. lib/queries.ts exports listsOf and resultOf
 * but nothing for a document, and this screen writes the job it is showing, so
 * it has to name the key to invalidate it.
 */
export function docKey(doctype: string, name: string) {
  return ["doc", doctype, name];
}

/** Whoever a name belongs to, or the account itself when nobody claimed it. */
export function personName(users: OperatingUser[] | undefined, id: string | null): string {
  if (!id) return "-";
  const found = (users ?? []).find((row) => row.name === id);
  return found?.full_name || id;
}
