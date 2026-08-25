# Any producer may write any job's money

A producer may log, correct and delete spending on a job they have never
worked on, and may walk any job's payment milestones through the collection
flow. There is no per-job boundary: `Job` grants read and write to Founder,
Producer and System Manager outright, and `auraos` installs no
`permission_query_conditions` hook, no `has_permission` hook and no User
Permission seeding, so `_check_job_permission` asks a question that has the
same answer for every job in the site.

**This is the model, decided rather than inherited.** The founder ruled on
2026-08-20 (#143), against a studio where everyone works everything and the
person nearest the receipt is the person who should be able to enter it. A
boundary here would mostly produce the shoot where the one producer who can
record the cash is the one on a plane.

The width is narrower than it first reads, because two of the money
endpoints were never producer-reachable:

- **Open to any producer, on any job:** `log_job_expense`,
  `update_job_expense`, `delete_job_expense`, `set_milestone_status` and
  `save_job_milestones`. Job Expense grants the Producer role create, write
  and delete; milestones are a child table of Job and ride on Job write, so
  both the collection flow and the plan behind it are open. The count is
  five after all - just not the five the ticket named.
- **Founder-only everywhere, on every job:** `record_job_advance` and
  `settle_job`. Job Advance and Job Settlement give the Producer role read
  and nothing else, so handing out and closing a float stay the founder's
  moves. That gate is about the act, not about whose job it is, and this
  decision does not touch it.

**Founder-only *figures* are a separate layer and are unaffected.** On Job
that layer is exactly one field - `commission_pct` at `permlevel` 1, granted
to Founder and System Manager only, proved three ways in `test_job.py`. The
rest of the profit block (`total_commission`, `cm`, `profit_before_tax`,
`tndn`, `net_profit`, `vat_payable`) sits at `permlevel` 1 on Deal, where the
pricing is still edited. A producer who may write every expense on a job
still cannot read what the company makes on it. Widening the write side has
never been what hides those numbers.

## The target model, when it is picked up

The founder's words for where this goes: *"ai cũng xem được nhưng có quyền
mới sửa được"* - **read for everyone, write only for those with the right**,
the right being an assignee (or team) on the Job.

- **Reads stay open, deliberately.** Boards, finance and reports must keep
  working for every role exactly as they do today. `_permitted_jobs()`
  already funnels every finance read through `frappe.get_list`, so a User
  Permission approach would silently narrow reads as a side effect - which
  is the one outcome this design rules out. A `has_permission` hook that
  discriminates on `ptype` is the shape that survives the constraint.
- **One change, all the write endpoints at once.** They share a single
  seam: all seven money-writing endpoints in `auraos/api.py` - the five
  above plus the two founder-only ones - go through
  `_check_job_permission(job, "write")`, and nothing writes job money
  around it. That is where the gate belongs, and a per-endpoint patch on
  any one of them is the failure mode to avoid - a boundary with a hole in
  it reads as a guarantee. The claim is mechanically checkable: no
  whitelisted endpoint that both writes a money doctype and names a job
  reaches the write without that call.
- Nothing is scheduled. This section is the brief, not a plan.

## Consequences

- **The absence of a refusal is now assertable as a presence.** The #125
  lane stalled here: it went to write "a producer on someone else's job is
  refused" and found no such refusal, and a test describing a product we do
  not have would have gone red against correct behaviour. With the ruling
  made, the positive is the thing to pin - `TestWhoMayWriteAJobsMoney` in
  `test_job_money.py` asserts that a second producer, with no connection to
  the job at all, may spend on it. When the target model lands, that class
  is the one that must go red on purpose and be rewritten; it is not
  incidental coverage.
- **Cash Transfer decided the same question the other way and said so.**
  `cash_transfer.py` reasons from the Company Expense precedent that money
  belonging to no job is founder-only, noting that #143's answer was about
  *job* money. That distinction is load-bearing: this decision is not a
  general "producers may move company money".
- **Deletion is included, not overlooked.** `delete_job_expense` walks its
  ledger entry back, so any producer can remove a payment from any job's
  accounting. Closed jobs refuse it (#123's freeze, gated in the doctype),
  which bounds the exposure in time but not by person.
- The day something other than this studio calls these endpoints, this file
  is the thing to reopen. `set_milestone_status` accepting an API demotion
  of a collected milestone (#126) is the same shape of question.
