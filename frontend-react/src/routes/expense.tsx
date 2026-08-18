// Logging a cost against a job, on real data.
//
// This is the one screen that is used standing up: a producer on set, holding a
// receipt, one hand on the phone. So it is a single narrow column, the amount
// is the only thing that is always typed and it has the focus on arrival, and
// the save button is thumb sized and full width.
//
// It is job scoped, the way the shipping Vue screen is, because an expense
// belongs to one job: the job rides in the URL (`/expense?job=JOB-0009`) and
// the screen is reached from that job. Arriving without one, from the nav, the
// screen asks which job first rather than guessing.

import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Camera, Check, ChevronRight, Clapperboard } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { useSession } from "@/components/aura/SessionProvider";
import { Card, Money } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { parseVnd, vnd } from "@/lib/format";
import { errorMessage, uploadFile } from "@/lib/frappe";
import { listsOf, resultOf, useList, useMethod, useMethodMutation } from "@/lib/queries";

type ExpenseSearch = { job: string | undefined };

export const Route = createFileRoute("/expense")({
  validateSearch: (search: Record<string, unknown>): ExpenseSearch => {
    const job = search["job"];
    return { job: typeof job === "string" && job ? job : undefined };
  },
  head: () => ({
    meta: [
      { title: "Log an expense - AuraOS" },
      {
        name: "description",
        content:
          "One-handed expense capture on set: amount, category, receipt photo, and the float it is spent out of.",
      },
      { property: "og:title", content: "Log an expense - AuraOS" },
      {
        property: "og:description",
        content: "Log a cost against a job in seconds and see the float update.",
      },
    ],
  }),
  component: ExpensePage,
});

// -- what the server sends --

type JobRow = { name: string; title: string | null; stage: string };

/** One person's float on one job, as auraos.api.job_money reports it. */
type Held = {
  holder: string;
  advanced: number;
  spent: number;
  settled: number;
  /** Positive: advance left to spend. Negative: their own money, so far. */
  amount: number;
  direction: string;
};

type JobMoney = { floats: Held[] };

type ExpenseResult = {
  name: string;
  amount: number;
  category: string | null;
  photo: string | null;
  float: Held;
};

function ExpensePage() {
  const { job } = Route.useSearch();

  // One list serves the picker and the job's name in the header, so choosing a
  // job costs no second request.
  const jobs = useList<JobRow>({
    doctype: "Job",
    fields: ["name", "title", "stage"],
    orderBy: "modified desc",
  });

  const openJobs = (jobs.data ?? []).filter((row) => row.stage !== "Complete");
  const chosen = (jobs.data ?? []).find((row) => row.name === job) ?? null;
  const jobLabel = chosen?.title || job || "";

  if (!job) {
    return (
      <AppShell title="Log an expense" meta="Which job is this cost against?">
        <div className="mx-auto max-w-md">
          <Card title="Pick the job" subtitle="An expense always belongs to one job">
            <QueryState
              query={jobs}
              isEmpty={() => openJobs.length === 0}
              empty={{
                title: "No job to spend on.",
                detail: "A won deal becomes a job, and it lands here.",
                icon: <Clapperboard className="size-6" strokeWidth={1.5} />,
              }}
            >
              {() => (
                <ul className="divide-y divide-border">
                  {openJobs.map((row) => (
                    <li key={row.name}>
                      <Link
                        to="/expense"
                        search={{ job: row.name }}
                        className="flex items-center gap-3 px-4 py-4 hover:bg-secondary/60"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium">
                            {row.title || row.name}
                          </div>
                          <div className="num mt-0.5 text-[11px] text-muted-foreground">
                            {row.name}
                          </div>
                        </div>
                        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </QueryState>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="Log an expense" meta={jobLabel}>
      {/* Keyed on the job so switching jobs starts a clean slate rather than
          carrying an amount typed against a different one. */}
      <ExpenseForm key={job} job={job} />
    </AppShell>
  );
}

function ExpenseForm({ job }: { job: string }) {
  const session = useSession();

  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<{ url: string; name: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [logged, setLogged] = useState<ExpenseResult[]>([]);

  const amountInput = useRef<HTMLInputElement>(null);
  const photoInput = useRef<HTMLInputElement>(null);

  // The thumb lands on the amount before the eye reads anything.
  useEffect(() => {
    amountInput.current?.focus();
  }, []);

  const money = useMethod<JobMoney>("auraos.api.job_money", { job });
  const categories = useMethod<string[]>("auraos.api.job_expense_categories", { job });

  const logExpense = useMethodMutation<ExpenseResult, Record<string, unknown>>(
    "auraos.api.log_job_expense",
    {
      invalidate: [listsOf("Job Expense"), resultOf("auraos.api.job_money")],
      onSuccess: (result) => {
        setLogged((rows) => [result, ...rows]);
        setAmount("");
        setNote("");
        setPhoto(null);
        setUploadError("");
        amountInput.current?.focus();
      },
    },
  );

  const value = parseVnd(amount);

  // The freshest float the server has said out loud: the one returned by the
  // last expense if there is one, otherwise the one job_money reported. Never
  // arithmetic done here.
  const heldFromMoney =
    (money.data?.floats ?? []).find((row) => row.holder === session.userId) ?? null;
  const held = logged[0]?.float ?? heldFromMoney;

  async function attachPhoto(file: File) {
    setUploadError("");
    setUploading(true);
    try {
      // Left unattached on purpose: log_job_expense re-parents the file onto
      // the expense it documents, and refuses one that is already attached.
      const uploaded = await uploadFile(file, { isPrivate: true, folder: "Home/Attachments" });
      if (uploaded.file_url) {
        setPhoto({ url: uploaded.file_url, name: uploaded.file_name ?? file.name });
      } else {
        setUploadError("The upload came back without a file.");
      }
    } catch (error) {
      setUploadError(errorMessage(error));
    } finally {
      setUploading(false);
      if (photoInput.current) photoInput.current.value = "";
    }
  }

  return (
    <form
      className="mx-auto max-w-md space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!value || uploading || logExpense.isPending) return;
        logExpense.mutate({
          job,
          amount: value,
          category: category || null,
          description: note || null,
          photo: photo?.url ?? null,
        });
      }}
    >
      <Link
        to="/jobs/$jobId"
        params={{ jobId: job }}
        className="inline-flex max-w-full items-center gap-1.5 py-1 text-xs text-muted-foreground hover:text-ember"
      >
        <ArrowLeft className="size-3.5 shrink-0" />
        <span className="truncate">Back to the job</span>
      </Link>

      <FloatCard money={money} held={held} />

      <Card>
        <div className="space-y-5 p-4">
          <div>
            <label className="label-caps" htmlFor="expense-amount">
              Amount
            </label>
            <div className="mt-1.5 flex items-center gap-2 rounded-xl border border-border px-3 py-3 focus-within:border-ember focus-within:ring-2 focus-within:ring-ember/20">
              <input
                id="expense-amount"
                ref={amountInput}
                inputMode="numeric"
                autoComplete="off"
                value={value ? vnd(value) : ""}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0"
                className="num w-full min-w-0 bg-transparent text-right text-3xl font-semibold outline-none placeholder:text-muted-foreground/40"
              />
              <span className="num shrink-0 text-xl text-muted-foreground">₫</span>
            </div>
          </div>

          <div>
            <span className="label-caps">Category</span>
            <QueryState query={categories} loadingRows={1}>
              {(titles) => (
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {titles.map((title) => (
                    <button
                      key={title}
                      type="button"
                      aria-pressed={category === title}
                      onClick={() => setCategory((current) => (current === title ? "" : title))}
                      className={
                        category === title
                          ? "rounded-full border border-transparent bg-primary px-4 py-2.5 text-sm text-primary-foreground"
                          : "rounded-full border border-border bg-card px-4 py-2.5 text-sm text-foreground hover:border-ember hover:text-ember"
                      }
                    >
                      {title}
                    </button>
                  ))}
                  {titles.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      This job was quoted with no packages - everything lands uncategorised.
                    </p>
                  ) : null}
                </div>
              )}
            </QueryState>
          </div>

          <div>
            <label className="label-caps" htmlFor="expense-note">
              Note
            </label>
            <input
              id="expense-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="What was it for? (optional)"
              className="mt-1.5 w-full rounded-xl border border-border bg-transparent px-3 py-3 text-sm outline-none focus:border-ember focus:ring-2 focus:ring-ember/20"
            />
          </div>

          <div>
            <span className="label-caps">Receipt</span>
            <input
              ref={photoInput}
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void attachPhoto(file);
              }}
            />
            <button
              type="button"
              disabled={uploading}
              onClick={() => photoInput.current?.click()}
              className="mt-1.5 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border-strong py-5 text-sm text-muted-foreground hover:border-ember hover:text-ember disabled:opacity-60"
            >
              <Camera className="size-4 shrink-0" />
              {uploading
                ? "Uploading..."
                : photo
                  ? "Replace receipt photo"
                  : "Attach receipt photo"}
            </button>
            {photo ? (
              <div className="mt-2 flex items-center gap-3 rounded-xl border border-border bg-secondary/50 p-2">
                <img
                  src={photo.url}
                  alt="Receipt"
                  className="size-12 shrink-0 rounded-lg object-cover"
                />
                <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                  {photo.name}
                </span>
                <button
                  type="button"
                  onClick={() => setPhoto(null)}
                  className="shrink-0 rounded-lg px-2.5 py-2 text-xs text-muted-foreground hover:text-ember"
                >
                  Remove
                </button>
              </div>
            ) : null}
            {uploadError ? <p className="mt-2 text-xs text-ember">{uploadError}</p> : null}
          </div>
        </div>
      </Card>

      <button
        type="submit"
        disabled={!value || uploading || logExpense.isPending}
        className="w-full rounded-xl bg-ember py-4 text-base font-semibold text-ember-foreground transition-opacity hover:opacity-90 disabled:bg-secondary disabled:text-muted-foreground disabled:opacity-100"
      >
        {logExpense.isPending ? "Saving..." : value ? `Log ${vnd(value)} ₫` : "Log expense"}
      </button>

      {logExpense.isError ? <ErrorState error={logExpense.error} className="px-0 py-3" /> : null}

      {logged.length > 0 ? (
        <Card title="Logged just now">
          <ul className="divide-y divide-border">
            {logged.map((row) => (
              <li key={row.name} className="flex items-center gap-2.5 px-4 py-3">
                <Check className="size-4 shrink-0 text-positive" strokeWidth={2} />
                <span className="min-w-0 flex-1 truncate text-sm">
                  {row.category || "Uncategorised"}
                </span>
                <Money value={row.amount} className="shrink-0 text-sm" />
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </form>
  );
}

/**
 * The only number worth carrying on this screen: the answer to "can I still pay
 * for this out of what I am holding?"
 *
 * Three states, one card. The sign lives in the caption so the figure itself
 * always reads positive, which is how a producer says it out loud.
 */
function FloatCard({
  money,
  held,
}: {
  money: ReturnType<typeof useMethod<JobMoney>>;
  held: Held | null;
}) {
  return (
    <Card>
      <div className="p-4">
        <div className="label-caps">Your float</div>
        <QueryState query={money} loadingRows={2}>
          {() =>
            held ? (
              <>
                <Money
                  value={held.amount >= 0 ? held.amount : -held.amount}
                  className={
                    held.amount >= 0
                      ? "mt-1 block text-2xl font-semibold"
                      : "mt-1 block text-2xl font-semibold text-ember"
                  }
                />
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {held.amount >= 0 ? "left of your advance" : "of your own money, so far"}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                No advance on this job yet - what you log comes back to you.
              </p>
            )
          }
        </QueryState>
      </div>
    </Card>
  );
}
