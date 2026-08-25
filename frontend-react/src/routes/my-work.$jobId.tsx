// One job as a crew member sees it: nothing priced (#41, ported at #165).
//
// Two reads. `auraos.api.crew_job` answers the job itself — and **the money is
// absent because it was never fetched**, not because this screen hides it. The
// endpoint reads a named list of five fields plus the client's name and the
// job's links; there is no document with the numbers stripped off afterwards,
// so there is nothing here for a bug to un-hide. `auraos.api.job_tasks` answers
// the plan, and it answers the same way to both kinds of user.
//
// **The same panel the producer reads.** `JobTasks` is mounted here unchanged:
// the plan is the plan, and a board showing one card is not a board. What
// narrows is what may be *written*, which the server decides — `can_plan` is
// false for a crew session, so the planning surface never renders, and the
// doctype's own permission lets them write the status and the note of their own
// task and no other.
//
// A producer or the founder opening this URL gets the same page. That is
// deliberate rather than an oversight: it is the money-free reading of a job,
// and there is no reason it should be refused to someone who could see more.

import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, FolderOpen, LinkIcon } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { JobTasks } from "@/components/aura/JobTasks";
import { Card, Pill } from "@/components/aura/primitives";
import { QueryState } from "@/components/aura/states";
import { useMethod } from "@/lib/queries";

/**
 * Pinned by auraos/auraos/doctype/job_task/test_job_task_crew_access.py.
 *
 * Note what this type cannot express: no quote total, no breakdown, no
 * milestones, no deal. The shape is the boundary.
 */
type CrewJob = {
  name: string;
  title: string;
  stage: string;
  files_location: string | null;
  job_owner: string | null;
  company_name: string | null;
  links: { label: string | null; url: string }[];
};

export const Route = createFileRoute("/my-work/$jobId")({
  head: () => ({
    meta: [
      { title: "Job - my work | AuraOS" },
      {
        name: "description",
        content: "A job's plan, its files and its links. No pricing and no money.",
      },
      { property: "og:title", content: "Job - AuraOS" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CrewJobPage,
});

function CrewJobPage() {
  const { jobId } = Route.useParams();
  const view = useMethod<CrewJob>("auraos.api.crew_job", { job: jobId });
  const doc = view.data;

  return (
    <AppShell
      title={doc?.title || jobId}
      meta={doc?.company_name ?? "My work"}
      actions={doc ? <Pill tone="outline">{doc.stage}</Pill> : null}
    >
      <div className="space-y-4">
        <Link
          to="/my-work"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="size-3.5" strokeWidth={1.75} />
          My work
        </Link>

        <QueryState query={view} loadingRows={3} isEmpty={() => false}>
          {(job) => (
            <>
              {job.files_location || job.links.length > 0 ? (
                <Card title="Where the material lives">
                  <div className="space-y-2 p-4">
                    {job.files_location ? (
                      <div className="flex items-start gap-2 text-sm">
                        <FolderOpen
                          className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                          strokeWidth={1.75}
                        />
                        <span className="break-all">{job.files_location}</span>
                      </div>
                    ) : null}
                    {job.links.map((link) => (
                      <div key={link.url} className="flex items-start gap-2 text-sm">
                        <LinkIcon
                          className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                          strokeWidth={1.75}
                        />
                        {/* noreferrer alongside noopener: a brief is a client's
                            private drive, and the referrer would name this app
                            to whatever is on the other end. */}
                        <a
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="break-all underline underline-offset-2 hover:text-foreground"
                        >
                          {link.label || link.url}
                        </a>
                      </div>
                    ))}
                  </div>
                </Card>
              ) : null}

              <JobTasks
                job={jobId}
                emptyMessage="Nothing on the plan yet — whoever is running this job writes it."
              />
            </>
          )}
        </QueryState>
      </div>
    </AppShell>
  );
}
