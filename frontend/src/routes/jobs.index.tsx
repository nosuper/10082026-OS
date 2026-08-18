import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Plus } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { KanbanBoard, ViewToggle, type KanbanColumn } from "@/components/aura/Kanban";
import { FormDialog, type FieldDef } from "@/components/aura/FormDialog";
import { jobsInProduction } from "@/data/fixture";

export const Route = createFileRoute("/jobs/")({
  head: () => ({
    meta: [
      { title: "Jobs in production — AuraOS" },
      {
        name: "description",
        content: "Every open job with stage, quoted value, crew float and collection status.",
      },
      { property: "og:title", content: "Jobs in production — AuraOS" },
      {
        property: "og:description",
        content: "Stage flow, quoted value, crew float and collection status per job.",
      },
    ],
  }),
  component: JobsPage,
});

const stageTone: Record<string, string> = {
  Production: "ink",
  "Post-production": "neutral",
  Delivery: "neutral",
  "Awaiting payment": "ember",
};

const extra = [
  { code: "JOB-0114", float: 12_500_000, collected: "Đã thu 50%" },
  { code: "JOB-0111", float: 0, collected: "Đã xuất hoá đơn" },
  { code: "JOB-0108", float: -3_200_000, collected: "Quá hạn 12 ngày" },
  { code: "JOB-0105", float: 0, collected: "Quá hạn 5 ngày" },
];

const jobStages = ["Pre-production", "Production", "Post-production", "Delivery", "Awaiting payment"];

type JobCardData = {
  job: string;
  client: string;
  stage: string;
  quoted: number;
  code: string;
  float: number;
  collected: string;
};

const seedJobs: JobCardData[] = jobsInProduction.map((j, i) => ({
  job: j.job,
  client: j.client,
  stage: j.stage,
  quoted: j.quoted,
  ...(extra[i] ?? { code: "", float: 0, collected: "" }),
}));

const jobFields: FieldDef[] = [
  { name: "job", label: "Job name", required: true, span: 2, placeholder: 'Brand film "Hạt Gạo Quê"' },
  { name: "client", label: "Client", required: true, placeholder: "Lộc Trời Agri" },
  { name: "deal", label: "Linked deal", placeholder: "DEAL-0182" },
  { name: "stage", label: "Stage", type: "select", options: jobStages },
  { name: "producer", label: "Producer in charge", placeholder: "Trần Quốc Bảo" },
  { name: "quoted", label: "Quoted value", type: "number", suffix: "₫", placeholder: "210000000" },
  { name: "float", label: "Crew float advance", type: "number", suffix: "₫", placeholder: "0" },
];


function JobCard({ j }: { j: JobCardData }) {
  return (
    <Link
      to="/jobs/$jobId"
      params={{ jobId: j.code }}
      className="block rounded-lg border border-border bg-card p-3 transition-shadow hover:border-border-strong hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium leading-snug">{j.job}</span>
        <span className="num text-[11px] text-muted-foreground">{j.code}</span>
      </div>
      <div className="mt-1 truncate text-xs text-muted-foreground">{j.client}</div>
      <div className="mt-2.5 flex items-baseline justify-between">
        <Money value={j.quoted} className="text-sm font-semibold" />
        <span className="text-[11px] text-muted-foreground">
          float <Money value={j.float} className={j.float < 0 ? "text-ember" : ""} />
        </span>
      </div>
      <div
        className={`mt-2 border-t border-border pt-2 text-[11px] ${j.collected.startsWith("Quá hạn") ? "text-ember" : "text-muted-foreground"}`}
      >
        {j.collected}
      </div>
    </Link>
  );
}

function JobsPage() {
  const [view, setView] = useState<"table" | "kanban">("table");
  const [jobs, setJobs] = useState<JobCardData[]>(seedJobs);
  const [newOpen, setNewOpen] = useState(false);
  const columns: KanbanColumn<JobCardData>[] = jobStages.map((s) => ({
    key: s,
    title: s,
    items: jobs.filter((j) => j.stage === s),
    focus: s === "Awaiting payment",
  }));

  const inProduction = jobs.reduce((s, j) => s + j.quoted, 0);
  const floatOutstanding = jobs.reduce((s, j) => s + Math.max(j.float, 0), 0);

  function createJob(v: Record<string, string>) {
    const nextCode = `JOB-${String(115 + jobs.length - seedJobs.length).padStart(4, "0")}`;
    setJobs((prev) => [
      {
        job: v["job"] ?? "Untitled job",
        client: v["client"] ?? "",
        stage: v["stage"] ?? "Pre-production",
        quoted: Number(v["quoted"] ?? 0) || 0,
        code: nextCode,
        float: Number(v["float"] ?? 0) || 0,
        collected: "Chưa thu",
      },
      ...prev,
    ]);
    setNewOpen(false);
  }

  return (
    <AppShell
      title="Jobs"
      meta={`${jobs.length} open jobs · ${new Intl.NumberFormat("vi-VN").format(inProduction)} ₫ in production`}
      actions={
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New job
        </button>
      }
    >
      <FormDialog
        open={newOpen}
        title="New job"
        subtitle="A job carries production stages, crew float and collections."
        fields={jobFields}
        submitLabel="Create job"
        onClose={() => setNewOpen(false)}
        onSubmit={createJob}
      />
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat
            label="In production"
            value={<Money value={inProduction} />}
            sub={`${jobs.length} open jobs`}
          />
          <Stat
            label="Crew float outstanding"
            value={<Money value={floatOutstanding} />}
            sub="advance − matched expenses"
          />
          <Stat
            label="Overdue collections"
            value={<Money value={86_500_000} />}
            sub="2 milestones past terms"
            alert
          />
        </div>

        <Card title="All jobs" action={<ViewToggle view={view} onChange={setView} />}>
          {view === "kanban" ? (
            <div className="p-3">
              <KanbanBoard
                columns={columns}
                total={(items) => items.reduce((s, j) => s + j.quoted, 0)}
                renderCard={(j) => <JobCard j={j} />}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Job</Th>
                    <Th>Client</Th>
                    <Th>Stage</Th>
                    <Th className="text-right">Quoted</Th>
                    <Th className="text-right">Crew float</Th>
                    <Th>Collection</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {jobs.map((j) => (
                    <tr key={j.code || j.job} className="hover:bg-secondary/50">
                      <Td>
                        <Link
                          to="/jobs/$jobId"
                          params={{ jobId: j.code }}
                          className="font-medium hover:text-ember"
                        >
                          {j.job}
                        </Link>
                        <div className="num mt-0.5 text-[11px] text-muted-foreground">{j.code}</div>
                      </Td>
                      <Td className="text-muted-foreground">{j.client}</Td>
                      <Td>
                        <Pill tone={stageTone[j.stage] ?? "neutral"}>{j.stage}</Pill>
                      </Td>
                      <Td className="text-right">
                        <Money value={j.quoted} />
                      </Td>
                      <Td
                        className={`text-right ${j.float < 0 ? "text-ember" : "text-muted-foreground"}`}
                      >
                        <Money value={j.float} />
                      </Td>
                      <Td
                        className={
                          j.collected.startsWith("Quá hạn") ? "text-ember" : "text-muted-foreground"
                        }
                      >
                        {j.collected}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

