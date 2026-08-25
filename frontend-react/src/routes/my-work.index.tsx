// A crew member's whole list: the jobs they hold a task on (#41, ported at #165).
//
// One read, `auraos.api.my_jobs`, and it is **money-free by construction rather
// than by redaction**. The endpoint builds its list from the tasks and then
// reads only the job fields a crew session is allowed — no carried breakdown,
// no packages, no quote totals, no milestones, no deal to follow back to the
// pricing. A payload that cannot hold those numbers cannot leak them, which is
// a stronger guarantee than a screen that fetches a job and hides the money.
//
// **Crew hold no permission on Job at all** — not read, not list, not search.
// That is one boundary instead of thirty field-level rules across the
// breakdown, the packages, the quote totals, the milestones and every money
// endpoint that gates on Job read. This screen exists because a crew member
// still needs somewhere to see their work, and `my_jobs` is that door.
//
// Producers and the founder can open this page too, and get their own tasks
// back. It is a personal list rather than a crew-only screen: the question
// "what is on my plate" is not answered anywhere else in the app.

import { createFileRoute, Link } from "@tanstack/react-router";
import { ClipboardList, FolderOpen } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { Card, Pill } from "@/components/aura/primitives";
import { QueryState } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useMethod } from "@/lib/queries";

/** Pinned by auraos/auraos/doctype/job_task/test_job_task_crew_access.py. */
type CrewJobRow = {
  name: string;
  title: string;
  stage: string;
  files_location: string | null;
  job_owner: string | null;
  company_name: string | null;
  /** Every task on the job, not only this session's. */
  task_count: number;
  /** This session's own unfinished tasks - the number that says "act". */
  open_tasks: number;
};

export const Route = createFileRoute("/my-work/")({
  head: () => ({
    meta: [
      { title: "My work - the jobs I'm on | AuraOS" },
      {
        name: "description",
        content:
          "Every job you hold a task on, with what is still open on your plate. No pricing, no money.",
      },
      { property: "og:title", content: "My work - AuraOS" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: MyWorkPage,
});

function MyWorkPage() {
  const mine = useMethod<CrewJobRow[]>("auraos.api.my_jobs");
  const jobs = mine.data ?? [];
  const openTotal = jobs.reduce((sum, job) => sum + job.open_tasks, 0);

  return (
    <AppShell
      title="My work"
      meta="The jobs you hold a task on"
      actions={
        mine.isSuccess && openTotal > 0 ? (
          <Pill tone="ember">{countLabel(openTotal, "task")} open</Pill>
        ) : null
      }
    >
      <QueryState
        query={mine}
        loadingRows={3}
        isEmpty={() => jobs.length === 0}
        empty={{
          title: "Nothing on your plate.",
          detail:
            "Jobs appear here once somebody puts a task on you. Nobody has yet, which is the whole of the answer.",
          icon: <ClipboardList className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {jobs.map((job) => (
              <Link
                key={job.name}
                to="/my-work/$jobId"
                params={{ jobId: job.name }}
                className="block rounded-xl border border-border bg-card p-4 transition-colors hover:border-border-strong"
              >
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="font-medium">{job.title || job.name}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {job.company_name ? `${job.company_name} · ` : ""}
                      <span className="num">{job.name}</span>
                    </div>
                  </div>
                  {/* The count that means "act", not the count that means
                      "exists": this session's unfinished tasks. A badge on the
                      job's total would be loudest on the busiest job rather
                      than on the one waiting for this person. */}
                  {job.open_tasks > 0 ? <Pill tone="ember">{job.open_tasks}</Pill> : null}
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <Pill tone="outline">{job.stage}</Pill>
                  <span className="label-caps">{countLabel(job.task_count, "task")}</span>
                </div>

                {job.files_location ? (
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <FolderOpen className="size-3.5 shrink-0" strokeWidth={1.75} />
                    <span className="truncate">{job.files_location}</span>
                  </div>
                ) : null}
              </Link>
            ))}
          </div>
        )}
      </QueryState>

      {jobs.length > 0 ? (
        <Card className="mt-4">
          <p className="p-4 text-xs leading-relaxed text-muted-foreground">
            This list is built from your tasks, so a job leaves it when your last task on it does.
            What a job is worth, what it cost and what the client was quoted are not part of this
            screen and are not fetched by it.
          </p>
        </Card>
      ) : null}
    </AppShell>
  );
}
