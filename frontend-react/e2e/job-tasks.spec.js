// The task plan and the managed lists, ported from Vue to React (#41, #29, #165).
//
// The crew *permission* boundary is pinned by 34 site tests in
// auraos/auraos/doctype/job_task/test_job_task_crew_access.py, and this file
// does not re-test it: the e2e suite has no crew session to sign in as, so a
// spec claiming to prove the boundary from the browser would be claiming more
// than it checks. What is asserted here is what only a browser can see — that
// the screens render the server's answer, and that the two rules a reader is
// most likely to get wrong survive the round trip:
//
// **`can_plan` decides the planning surface, not a role read in the browser.**
// **`can_manage` is per list, not per user** — a producer manages deal sources
// and not project types, and that is one screen telling the truth rather than
// two.
//
// Everything is written as a change against the state a moment earlier, so the
// seed can grow underneath this file without touching it. The unwind is in a
// finally block because workers is 1 and fullyParallel is off: a spec that
// failed halfway would otherwise hand every later file a different site.

import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { callAs } from "./call.js";
import { JOB_DEAL } from "./fixture.js";
import { firstName, openJob, openJobTab } from "./records.js";

const producerTest = test.extend({ storageState: producerState });

const PLAN = "auraos.api.job_tasks";
const VOCABULARIES = "auraos.api.get_vocabularies";

/** Mirrors job_task.STATUSES. Asserted against the server's own list below. */
const STATUSES = ["To do", "In progress", "Blocked", "In review", "Done"];

async function openDashboard(page) {
  await page.goto("/aura-next/");
  await expect(
    page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ }),
  ).toBeVisible();
}

// -- the plan --

test("the plan is the doctype's statuses, and the planner is told they may plan", async ({
  page,
}) => {
  await openDashboard(page);
  const job = await openJob(page);
  const answer = await callAs(page, PLAN, { job });

  expect(answer.status, `the plan was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const plan = answer.body.message;

  // The columns of a board are the server's list. A copy in the browser is how
  // a column appears out of a spelling mistake.
  expect(plan.statuses).toEqual(STATUSES);
  expect(plan.can_plan).toBe(true);
  expect(typeof plan.user).toBe("string");
  // No money reaches this payload, which is what makes one component safe for
  // a session holding no permission on Job at all.
  const keys = new Set(Object.keys(plan.tasks[0] ?? {}));
  for (const forbidden of ["amount", "quote_total", "margin", "commission_pct"]) {
    expect(keys.has(forbidden), `the plan carries ${forbidden}`).toBe(false);
  }
});

test("a task written through the screen appears on all three views", async ({ page }) => {
  await openDashboard(page);
  const job = await openJob(page);

  const before = (await callAs(page, PLAN, { job })).body.message.tasks.length;
  const title = "Playwright spec task";
  const created = await callAs(page, "auraos.api.save_job_task", {
    job,
    values: { title, start_date: "2026-03-02", end_date: "2026-03-06", status: "To do" },
  });
  expect(created.status, `the task was refused: ${JSON.stringify(created.body)}`).toBe(200);
  const task = created.body.message.name;

  try {
    const after = (await callAs(page, PLAN, { job })).body.message.tasks;
    expect(after.length).toBe(before + 1);

    const panel = await openJobTab(page, job, "Tasks");

    // List: the row is there. Read as an input value rather than as text,
    // because a session that may plan gets an editable title - `getByText`
    // finds nothing in a textbox, which is what this assertion learned the
    // hard way. The label is the stable handle either way.
    await expect(panel.getByLabel(`Title of ${title}`)).toHaveValue(title);

    // Board: every column the server named is drawn, even the empty ones -
    // a kanban missing its empty columns is a different board.
    await panel.getByRole("tab", { name: "Board" }).click();
    for (const status of STATUSES) {
      await expect(panel.getByText(status, { exact: true }).first()).toBeVisible();
    }

    // Timeline: the task has both dates, so it has a bar. Text here, not a
    // value: the timeline is a reading of the plan and never an editor of it,
    // whoever is looking.
    await panel.getByRole("tab", { name: "Timeline" }).click();
    await expect(panel.getByText(title, { exact: true }).first()).toBeVisible();

    // Nothing anywhere reads as a broken number. textContent, not innerText:
    // innerText applies text-transform, so a NaN inside a label-caps element
    // would come back as NAN and slip past.
    const text = String((await panel.textContent()) ?? "");
    expect(text).not.toMatch(/NaN|undefined|Infinity/);

    // Moving the card is a real write, and the server is what holds it.
    const moved = await callAs(page, "auraos.api.set_job_task_status", {
      task,
      status: "In progress",
    });
    expect(moved.status).toBe(200);
    const reread = (await callAs(page, PLAN, { job })).body.message.tasks;
    expect(reread.find((row) => row.name === task).status).toBe("In progress");
  } finally {
    const gone = await callAs(page, "auraos.api.delete_job_task", { task });
    expect(gone.status, `the spec could not remove ${task}`).toBe(200);
  }

  // Derived, not stored: with the task gone the plan is what it was.
  const closing = (await callAs(page, PLAN, { job })).body.message.tasks;
  expect(closing.length).toBe(before);
});

test("my work lists the jobs this session holds a task on", async ({ page }) => {
  await openDashboard(page);
  const job = await openJob(page);

  const answer = await callAs(page, "auraos.api.my_jobs");
  expect(answer.status, `my_jobs was refused: ${JSON.stringify(answer.body)}`).toBe(200);

  // Money-free by construction rather than by redaction: the endpoint reads a
  // named list of fields, so there is nothing here for a bug to un-hide.
  for (const row of answer.body.message) {
    for (const forbidden of ["quote_total", "quote_subtotal", "commission_pct", "margin"]) {
      expect(forbidden in row, `my_jobs carries ${forbidden}`).toBe(false);
    }
  }

  await page.goto("/aura-next/my-work");
  await expect(page.getByRole("heading", { name: "My work", exact: true })).toBeVisible();

  // And the money-free reading of one job renders too.
  const crew = await callAs(page, "auraos.api.crew_job", { job });
  expect(crew.status, `crew_job was refused: ${JSON.stringify(crew.body)}`).toBe(200);
  for (const forbidden of ["quote_total", "cost_lines", "packages", "payment_milestones"]) {
    expect(forbidden in crew.body.message, `crew_job carries ${forbidden}`).toBe(false);
  }
});

// -- the managed lists --

test("the founder manages every list", async ({ page }) => {
  await openDashboard(page);
  const answer = await callAs(page, VOCABULARIES);
  expect(answer.status, `the lists were refused: ${JSON.stringify(answer.body)}`).toBe(200);

  const lists = answer.body.message;
  expect(lists.length).toBeGreaterThan(0);
  for (const vocab of lists) {
    expect(vocab.can_manage, `${vocab.key} is not manageable by the founder`).toBe(true);
    // The count is what makes a refusal readable before it happens.
    for (const value of vocab.values) {
      expect(typeof value.in_use).toBe("number");
    }
  }
});

// The rule this screen exists to show, and the one a single `can_manage` on
// the session would have got wrong.
producerTest("a producer manages deal sources and not project types", async ({ page }) => {
  await openDashboard(page);
  const answer = await callAs(page, VOCABULARIES);
  expect(answer.status, `the lists were refused a producer: ${JSON.stringify(answer.body)}`).toBe(
    200,
  );

  const byKey = Object.fromEntries(answer.body.message.map((v) => [v.key, v]));
  expect(byKey.source.can_manage, "a producer cannot manage deal sources").toBe(true);
  expect(byKey.project_type.can_manage, "a producer can manage project types").toBe(false);

  // Refused at the server too, not merely absent from the screen - the screen
  // hiding a control is the courtesy, this is the guarantee.
  const refused = await callAs(page, "auraos.api.add_vocabulary_value", {
    kind: "project_type",
    value: "Playwright spec type",
  });
  expect(refused.status, `a producer added a project type: ${JSON.stringify(refused.body)}`).toBe(
    403,
  );
  expect(refused.excType).toBe("PermissionError");
});

producerTest(
  "settings shows a producer the lists it may manage, not a locked page",
  async ({ page }) => {
    const failures = [];
    page.on("pageerror", (error) => failures.push(error.message));

    await page.goto("/aura-next/settings");
    await expect(page.getByRole("heading", { name: "Company settings" })).toBeVisible();

    // T3.5 stopped Settings being a founder-only door. A producer opening it
    // must find their own section rather than a wholesale refusal - which is
    // the screen the ticket exists to replace.
    await expect(page.getByRole("heading", { name: "Managed lists" })).toBeVisible();
    await expect(page.getByText("Deal sources", { exact: true })).toBeVisible();

    // And the founder half is still the founder's.
    await expect(page.getByText(/the margin floor, tiers, positioning/)).toBeVisible();
    expect(failures).toEqual([]);
  },
);

test("a value still in use cannot be removed, and the refusal says how many hold it", async ({
  page,
}) => {
  await openDashboard(page);

  // **Built here rather than found in the seed.** An earlier version of this
  // test looked for a source some deal already held and skipped when it found
  // none - and neither seed has ever set `Deal.source`, so it skipped every
  // run and read as coverage while proving nothing. A test that can only skip
  // is worse than no test, because the file still lists it.
  const value = "Playwright spec source";
  const deal = await firstName(page, "Deal", { title: JOB_DEAL });
  expect(deal, "the seeded deal is missing, so this test has nothing to attach to").toBeTruthy();

  const added = await callAs(page, "auraos.api.add_vocabulary_value", {
    kind: "source",
    value,
  });
  expect(added.status, `the source was refused: ${JSON.stringify(added.body)}`).toBe(200);

  try {
    // Nothing holds it yet, so it is removable - the control for the refusal
    // below. Without it this test would pass on a server that refused every
    // removal.
    const free = added.body.message.find((v) => v.key === "source");
    expect(free.values.find((v) => v.name === value).in_use).toBe(0);

    const attached = await callAs(page, "frappe.client.set_value", {
      doctype: "Deal",
      name: deal,
      fieldname: "source",
      value,
    });
    expect(attached.status, `could not put the source on the deal`).toBe(200);

    // The count is the server's, and it is what makes the refusal readable
    // before it happens.
    const held = (await callAs(page, VOCABULARIES)).body.message
      .find((v) => v.key === "source")
      .values.find((v) => v.name === value);
    expect(held.in_use).toBe(1);

    const refused = await callAs(page, "auraos.api.remove_vocabulary_value", {
      kind: "source",
      value,
    });
    // Asserted by exception class rather than by HTTP status: the status
    // Frappe maps a ValidationError to is the framework's business and has
    // moved between versions, while the class is the contract
    // auraos.lib.vocabulary actually promises.
    expect(
      refused.status,
      `a value on a deal was removed: ${JSON.stringify(refused.body)}`,
    ).not.toBe(200);
    expect(refused.excType).toBe("ValidationError");

    // The number is in the refusal, because "cannot remove" without it is a
    // dead end and "cannot remove, one deal holds it" is a next step.
    expect(JSON.stringify(refused.body ?? {})).toContain("1");
  } finally {
    // Put the deal back first: while it holds the value, the value cannot be
    // removed - which is the rule this test just proved.
    await callAs(page, "frappe.client.set_value", {
      doctype: "Deal",
      name: deal,
      fieldname: "source",
      value: "",
    });
    const gone = await callAs(page, "auraos.api.remove_vocabulary_value", {
      kind: "source",
      value,
    });
    expect(gone.status, `the spec could not remove ${value}`).toBe(200);
  }
});
