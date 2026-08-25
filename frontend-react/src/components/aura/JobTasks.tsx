// One plan, three ways of reading it: the list to write it, the board to work
// it, the timeline to see whether it fits (#41, ported at #165).
//
// **One component, two audiences.** The job page mounts this and so does the
// crew job view, and it is the same component because it is the same plan.
// What differs is what the server says the session may do, which arrives as
// `can_plan` in the payload — asked rather than inferred from a role, because
// the rule about who may plan lives on the server and a browser guessing at it
// would guess wrong on the day the rule changes.
//
// **Crew see the whole plan, not only their own row.** A board showing one
// card is not a board, and knowing who else is on the job is not knowing what
// anyone is paid. What a crew session may *write* is narrower: its own card's
// status and note, which is the doctype's own permission and is enforced there.
//
// **No money reaches this file.** The plan carries titles, crafts, people,
// dates and statuses. That is what makes it safe to render for a session that
// holds no permission on Job at all.
//
// The statuses are the server's list, not a copy — see lib/tasks.ts for why
// that matters and what happened to the Vue original's palette.

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Plus, Trash2 } from "lucide-react";

import { Card, Pill, Td, Th, inputClass } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { countLabel, formatDate } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";
import {
  DAY_MS,
  FALLBACK_STATUSES,
  daysLate,
  parseDate,
  personLabel,
  shortDate,
  statusTone,
} from "@/lib/tasks";
import { cn } from "@/lib/utils";

// -- what the server sends --
//
// Pinned by auraos/auraos/doctype/job_task/test_job_task.py and, for the crew
// boundary, test_job_task_crew_access.py.

export type JobTask = {
  name: string;
  job: string;
  title: string;
  craft: string | null;
  assigned_to: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string;
  notes: string | null;
};

export type TaskPlan = {
  tasks: JobTask[];
  /** The doctype's own list, in board-column order. */
  statuses: string[];
  /** {email: full name} for the people on this job. Crew cannot list users. */
  people: Record<string, string>;
  /** Whether this session may plan, as opposed to only moving its own card. */
  can_plan: boolean;
  user: string;
};

type CraftOption = string;
type Person = { name: string; full_name: string };

const VIEWS = ["List", "Board", "Timeline"] as const;
type View = (typeof VIEWS)[number];

/** A task being written but not yet saved. */
type Draft = {
  title: string;
  craft: string | null;
  assigned_to: string | null;
  start_date: string | null;
  end_date: string | null;
};

const emptyDraft = (): Draft => ({
  title: "",
  craft: null,
  assigned_to: null,
  start_date: null,
  end_date: null,
});

export function JobTasks({ job, emptyMessage }: { job: string; emptyMessage: string }) {
  const [view, setView] = useState<View>("List");
  const [draft, setDraft] = useState<Draft | null>(null);

  const plan = useMethod<TaskPlan>("auraos.api.job_tasks", { job });
  const data = plan.data;
  const tasks = data?.tasks ?? [];
  const statuses = data?.statuses ?? [...FALLBACK_STATUSES];
  const canPlan = Boolean(data?.can_plan);
  const people = data?.people ?? {};
  const me = data?.user;

  // Fetched only once the plan says this session may plan: both endpoints
  // refuse a crew session, and asking for a guaranteed 403 on every visit is
  // noise in the network log and in the server's error rate.
  const crafts = useMethod<CraftOption[]>("auraos.api.task_crafts", undefined, {
    enabled: canPlan,
  });
  const assignable = useMethod<Person[]>("auraos.api.assignable_users", undefined, {
    enabled: canPlan,
  });

  const invalidate = [resultOf("auraos.api.job_tasks"), resultOf("auraos.api.my_jobs")];
  const save = useMethodMutation<JobTask, Record<string, unknown>>("auraos.api.save_job_task", {
    invalidate,
    onSuccess: () => setDraft(null),
  });
  const drop = useMethodMutation<unknown, Record<string, unknown>>("auraos.api.delete_job_task", {
    invalidate,
  });
  const setStatus = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.set_job_task_status",
    { invalidate },
  );
  const setNote = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.set_job_task_note",
    { invalidate },
  );

  /** Whose card this is, and therefore who may move it. */
  const mine = (task: JobTask) => Boolean(task.assigned_to) && task.assigned_to === me;
  const canMove = (task: JobTask) => canPlan || mine(task);

  const move = (task: JobTask, status: string) => {
    if (task.status === status || !canMove(task)) return;
    setStatus.mutate({ task: task.name, status });
  };

  const lateCount = tasks.filter((task) => daysLate(task)).length;
  const error = save.error || drop.error || setStatus.error || setNote.error;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" className="flex items-center gap-0.5 rounded-lg bg-secondary p-0.5">
          {VIEWS.map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={view === option}
              onClick={() => setView(option)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                view === option
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {option}
            </button>
          ))}
        </div>
        <span className="label-caps">{countLabel(tasks.length, "task")}</span>
        {lateCount > 0 ? (
          <Pill tone="ember">
            <AlertCircle className="size-3" strokeWidth={2} />
            {lateCount} overdue
          </Pill>
        ) : null}
        {canPlan ? (
          <button
            type="button"
            onClick={() => setDraft(emptyDraft())}
            className="ml-auto inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus className="size-3.5" strokeWidth={2} />
            Add task
          </button>
        ) : null}
      </div>

      {error ? <ErrorState error={error} /> : null}

      <QueryState
        query={plan}
        loadingRows={4}
        isEmpty={() => tasks.length === 0 && !draft}
        empty={{ title: "No tasks yet.", detail: emptyMessage }}
      >
        {() => (
          <>
            {view === "List" ? (
              <TaskList
                tasks={tasks}
                statuses={statuses}
                people={people}
                canPlan={canPlan}
                canMove={canMove}
                crafts={crafts.data ?? []}
                assignable={assignable.data ?? []}
                draft={draft}
                onDraft={setDraft}
                onSaveDraft={(values) => save.mutate({ job, values })}
                onPatch={(task, values) =>
                  save.mutate({ job, values: { name: task.name, ...values } })
                }
                onMove={move}
                onNote={(task, note) => {
                  if ((task.notes || "") === note) return;
                  setNote.mutate({ task: task.name, note });
                }}
                onDelete={(task) => drop.mutate({ task: task.name })}
              />
            ) : null}

            {view === "Board" ? (
              <TaskBoard
                tasks={tasks}
                statuses={statuses}
                people={people}
                canMove={canMove}
                onMove={move}
              />
            ) : null}

            {view === "Timeline" ? <TaskTimeline tasks={tasks} people={people} /> : null}
          </>
        )}
      </QueryState>
    </div>
  );
}

// -- list: the plan as it is written --

function TaskList({
  tasks,
  statuses,
  people,
  canPlan,
  canMove,
  crafts,
  assignable,
  draft,
  onDraft,
  onSaveDraft,
  onPatch,
  onMove,
  onNote,
  onDelete,
}: {
  tasks: JobTask[];
  statuses: string[];
  people: Record<string, string>;
  canPlan: boolean;
  canMove: (task: JobTask) => boolean;
  crafts: string[];
  assignable: Person[];
  draft: Draft | null;
  onDraft: (draft: Draft | null) => void;
  onSaveDraft: (values: Draft) => void;
  onPatch: (task: JobTask, values: Partial<JobTask>) => void;
  onMove: (task: JobTask, status: string) => void;
  onNote: (task: JobTask, note: string) => void;
  onDelete: (task: JobTask) => void;
}) {
  const titleRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (draft) titleRef.current?.focus();
  }, [draft]);

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[46rem]">
          <thead className="border-b border-border">
            <tr>
              <Th className="w-full">Task</Th>
              <Th>Craft</Th>
              <Th>Who</Th>
              <Th>Start</Th>
              <Th>Due</Th>
              <Th>Status</Th>
              {canPlan ? <Th /> : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {draft ? (
              <tr className="bg-secondary/50">
                <Td>
                  <input
                    ref={titleRef}
                    aria-label="What has to happen"
                    placeholder="What has to happen"
                    value={draft.title}
                    onChange={(e) => onDraft({ ...draft, title: e.target.value })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && draft.title.trim()) onSaveDraft(draft);
                      if (e.key === "Escape") onDraft(null);
                    }}
                    className={inputClass}
                  />
                </Td>
                <Td>
                  <PickCraft
                    value={draft.craft}
                    crafts={crafts}
                    onChange={(craft) => onDraft({ ...draft, craft })}
                  />
                </Td>
                <Td>
                  <PickPerson
                    value={draft.assigned_to}
                    people={assignable}
                    onChange={(who) => onDraft({ ...draft, assigned_to: who })}
                  />
                </Td>
                <Td>
                  <DateField
                    value={draft.start_date}
                    onChange={(d) => onDraft({ ...draft, start_date: d })}
                  />
                </Td>
                <Td>
                  <DateField
                    value={draft.end_date}
                    onChange={(d) => onDraft({ ...draft, end_date: d })}
                  />
                </Td>
                <Td colSpan={2}>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      disabled={!draft.title.trim()}
                      onClick={() => onSaveDraft(draft)}
                      className="rounded-lg bg-primary px-2 py-1 text-xs font-medium text-primary-foreground disabled:opacity-50"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => onDraft(null)}
                      className="rounded-lg border border-border px-2 py-1 text-xs"
                    >
                      Cancel
                    </button>
                  </div>
                </Td>
              </tr>
            ) : null}

            {tasks.map((task) => {
              const late = daysLate(task);
              return (
                <tr key={task.name} className="align-top hover:bg-secondary/40">
                  <Td>
                    {canPlan ? (
                      <input
                        aria-label={`Title of ${task.title}`}
                        defaultValue={task.title}
                        onBlur={(e) => {
                          const title = e.target.value.trim();
                          if (title && title !== task.title) onPatch(task, { title });
                        }}
                        className={inputClass}
                      />
                    ) : (
                      <span className="text-sm font-medium">{task.title}</span>
                    )}
                    <NoteField task={task} canWrite={canMove(task)} onNote={onNote} />
                  </Td>
                  <Td>
                    {canPlan ? (
                      <PickCraft
                        value={task.craft}
                        crafts={crafts}
                        onChange={(craft) => onPatch(task, { craft })}
                      />
                    ) : (
                      <span className="text-xs text-muted-foreground">{task.craft || "—"}</span>
                    )}
                  </Td>
                  <Td>
                    {canPlan ? (
                      <PickPerson
                        value={task.assigned_to}
                        people={assignable}
                        onChange={(who) => onPatch(task, { assigned_to: who })}
                      />
                    ) : (
                      <span className="text-xs">{personLabel(task.assigned_to, people)}</span>
                    )}
                  </Td>
                  <Td>
                    {canPlan ? (
                      <DateField
                        value={task.start_date}
                        onChange={(start_date) => onPatch(task, { start_date })}
                      />
                    ) : (
                      <span className="num text-xs">{formatDate(task.start_date)}</span>
                    )}
                  </Td>
                  <Td>
                    {canPlan ? (
                      <DateField
                        value={task.end_date}
                        onChange={(end_date) => onPatch(task, { end_date })}
                      />
                    ) : (
                      <span className="num text-xs">{formatDate(task.end_date)}</span>
                    )}
                    {late ? <div className="mt-0.5 text-xs text-ember">{late}d late</div> : null}
                  </Td>
                  <Td>
                    {canMove(task) ? (
                      <select
                        aria-label={`Status of ${task.title}`}
                        value={task.status}
                        onChange={(e) => onMove(task, e.target.value)}
                        className={cn(inputClass, "w-32")}
                      >
                        {statuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Pill tone={statusTone(task.status)}>{task.status}</Pill>
                    )}
                  </Td>
                  {canPlan ? (
                    <Td>
                      <button
                        type="button"
                        aria-label={`Remove ${task.title}`}
                        onClick={() => onDelete(task)}
                        className="rounded-lg border border-border p-1.5 text-muted-foreground hover:bg-secondary hover:text-ember"
                      >
                        <Trash2 className="size-3.5" strokeWidth={1.75} />
                      </button>
                    </Td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/**
 * The note on a task - the other half of what a crew member may write.
 *
 * "Waiting on the client's logo" is the whole reason for letting an editor
 * onto the job at all, so it is editable by whoever may move the card rather
 * than by planners only. Saved on blur, and only when it actually changed.
 */
function NoteField({
  task,
  canWrite,
  onNote,
}: {
  task: JobTask;
  canWrite: boolean;
  onNote: (task: JobTask, note: string) => void;
}) {
  if (!canWrite) {
    return task.notes ? (
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{task.notes}</p>
    ) : null;
  }
  return (
    <input
      aria-label={`Note on ${task.title}`}
      placeholder="Add a note"
      defaultValue={task.notes ?? ""}
      onBlur={(e) => onNote(task, e.target.value.trim())}
      className="mt-1 w-full border-none bg-transparent px-0 text-xs text-muted-foreground outline-none placeholder:text-muted-foreground/60 focus:text-foreground"
    />
  );
}

function PickCraft({
  value,
  crafts,
  onChange,
}: {
  value: string | null;
  crafts: string[];
  onChange: (value: string | null) => void;
}) {
  return (
    <select
      aria-label="Craft"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className={cn(inputClass, "w-28")}
    >
      <option value="">—</option>
      {crafts.map((craft) => (
        <option key={craft} value={craft}>
          {craft}
        </option>
      ))}
    </select>
  );
}

function PickPerson({
  value,
  people,
  onChange,
}: {
  value: string | null;
  people: Person[];
  onChange: (value: string | null) => void;
}) {
  return (
    <select
      aria-label="Assigned to"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className={cn(inputClass, "w-32")}
    >
      <option value="">Unassigned</option>
      {people.map((person) => (
        <option key={person.name} value={person.name}>
          {person.full_name || person.name}
        </option>
      ))}
    </select>
  );
}

function DateField({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  return (
    <input
      type="date"
      aria-label="Date"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className={cn(inputClass, "num w-32")}
    />
  );
}

// -- board: the plan as it is worked --

function TaskBoard({
  tasks,
  statuses,
  people,
  canMove,
  onMove,
}: {
  tasks: JobTask[];
  statuses: string[];
  people: Record<string, string>;
  canMove: (task: JobTask) => boolean;
  onMove: (task: JobTask, status: string) => void;
}) {
  const [dragged, setDragged] = useState<JobTask | null>(null);
  const [over, setOver] = useState<string | null>(null);

  return (
    <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
      {statuses.map((status) => {
        const column = tasks.filter((task) => task.status === status);
        return (
          <div
            key={status}
            onDragOver={(e) => {
              e.preventDefault();
              setOver(status);
            }}
            onDragLeave={(e) => {
              if (e.currentTarget.contains(e.relatedTarget as Node)) return;
              setOver((current) => (current === status ? null : current));
            }}
            onDrop={() => {
              const task = dragged;
              setDragged(null);
              setOver(null);
              if (task) onMove(task, status);
            }}
            className={cn(
              "rounded-xl border bg-card p-2 transition-colors",
              over === status ? "border-border-strong bg-secondary/60" : "border-border",
            )}
          >
            <div className="mb-2 flex items-baseline justify-between px-1">
              <span className="label-caps">{status}</span>
              <span className="num text-xs text-muted-foreground">{column.length}</span>
            </div>
            <div className="space-y-2">
              {column.map((task) => {
                const late = daysLate(task);
                const movable = canMove(task);
                return (
                  <div
                    key={task.name}
                    draggable={movable}
                    onDragStart={() => setDragged(task)}
                    onDragEnd={() => {
                      setDragged(null);
                      setOver(null);
                    }}
                    className={cn(
                      "rounded-lg border border-border bg-background p-2",
                      movable ? "cursor-grab active:cursor-grabbing" : "opacity-80",
                    )}
                  >
                    <div className="text-sm font-medium">{task.title}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                      <span>{personLabel(task.assigned_to, people)}</span>
                      {task.craft ? <span>· {task.craft}</span> : null}
                      {task.end_date ? (
                        <span className="num">· {shortDate(task.end_date)}</span>
                      ) : null}
                    </div>
                    {late ? (
                      <div className="mt-1">
                        <Pill tone="ember">{late}d late</Pill>
                      </div>
                    ) : null}
                    {task.notes ? (
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {task.notes}
                      </p>
                    ) : null}
                  </div>
                );
              })}
              {column.length === 0 ? (
                <p className="px-1 py-2 text-xs text-muted-foreground">Nothing here.</p>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// -- timeline: whether the plan fits --

function TaskTimeline({ tasks, people }: { tasks: JobTask[]; people: Record<string, string> }) {
  const scheduled = tasks.filter((task) => task.start_date && task.end_date);
  const unscheduled = tasks.filter((task) => !(task.start_date && task.end_date));

  // The window the bars are drawn in: the whole plan, padded by a day at each
  // end so a bar never sits flush against the edge.
  const starts = scheduled.map((t) => parseDate(t.start_date)?.getTime() ?? 0);
  const ends = scheduled.map((t) => parseDate(t.end_date)?.getTime() ?? 0);
  const span =
    starts.length > 0
      ? {
          from: Math.min(...starts) - DAY_MS,
          to: Math.max(...ends) + DAY_MS,
        }
      : null;
  const days = span ? Math.max(1, (span.to - span.from) / DAY_MS) : 1;

  const positionOf = (value: string | null) => {
    const at = parseDate(value);
    if (!span || !at) return null;
    return ((at.getTime() - span.from) / DAY_MS / days) * 100;
  };

  // A tick at the first of each month the plan crosses; a short plan that
  // crosses none is ticked at its two ends instead, so the ruler is never
  // blank.
  const ticks: { at: number; label: string }[] = [];
  if (span) {
    const cursor = new Date(span.from);
    cursor.setDate(1);
    cursor.setMonth(cursor.getMonth() + 1);
    while (cursor.getTime() <= span.to) {
      ticks.push({
        at: ((cursor.getTime() - span.from) / DAY_MS / days) * 100,
        label: `Thg ${cursor.getMonth() + 1}`,
      });
      cursor.setMonth(cursor.getMonth() + 1);
    }
    if (ticks.length === 0) {
      ticks.push({ at: 0, label: shortDate(new Date(span.from).toISOString()) });
      ticks.push({ at: 100, label: shortDate(new Date(span.to).toISOString()) });
    }
  }

  // Today, when the plan actually crosses it. A "today" line outside the
  // window would sit pinned to an edge and read as a deadline.
  const todayAt = (() => {
    if (!span) return null;
    const now = new Date();
    const at = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if (at < span.from || at > span.to) return null;
    return ((at - span.from) / DAY_MS / days) * 100;
  })();

  return (
    <Card>
      {span ? (
        <div className="space-y-2 p-4">
          <div className="relative h-4 border-b border-border">
            {ticks.map((tick) => (
              <span
                key={`${tick.at}-${tick.label}`}
                className="label-caps absolute -translate-x-1/2"
                style={{ left: `${tick.at}%` }}
              >
                {tick.label}
              </span>
            ))}
          </div>

          <div className="relative space-y-1.5">
            {todayAt !== null ? (
              <div
                aria-hidden
                className="pointer-events-none absolute inset-y-0 w-px bg-ember/60"
                style={{ left: `${todayAt}%` }}
              />
            ) : null}

            {scheduled.map((task) => {
              const from = positionOf(task.start_date);
              const to = positionOf(task.end_date);
              const late = daysLate(task);
              // A one-day task ends where it starts, so the bar is widened to
              // the day it occupies rather than rendering as a hairline.
              const width = from === null || to === null ? 0 : Math.max(to - from, 100 / days);
              return (
                <div key={task.name} className="group relative h-7">
                  <div
                    className={cn(
                      "absolute inset-y-1 flex items-center overflow-hidden rounded-md px-2",
                      late ? "bg-ember" : "bg-primary",
                    )}
                    style={{ left: `${from ?? 0}%`, width: `${width}%` }}
                    title={`${task.title} · ${shortDate(task.start_date)}–${shortDate(task.end_date)}`}
                  >
                    <span className="truncate text-xs font-medium text-primary-foreground">
                      {task.title}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-2 text-xs text-muted-foreground">
            {scheduled.map((task) => (
              <span key={task.name}>
                <span className="text-foreground">{task.title}</span> ·{" "}
                {personLabel(task.assigned_to, people)} ·{" "}
                <span className="num">
                  {shortDate(task.start_date)}–{shortDate(task.end_date)}
                </span>
              </span>
            ))}
          </div>
        </div>
      ) : (
        <p className="p-4 text-xs text-muted-foreground">
          Nothing on the plan has both a start and a due date yet, so there is no timeline to draw.
        </p>
      )}

      {/* Undated work has to live somewhere on all three views: written down
          before it is scheduled is a real state, and a timeline that dropped
          it would be the one view where it vanished. */}
      {unscheduled.length > 0 ? (
        <div className="border-t border-border p-4">
          <p className="label-caps">Not scheduled</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {unscheduled.map((task) => (
              <Pill key={task.name} tone={statusTone(task.status)}>
                {task.title} · {personLabel(task.assigned_to, people)}
              </Pill>
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}
