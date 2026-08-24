"""One piece of work on a job, and the door it opens for crew (T7.1, issue #41).

A job task is pure scheduling: a title, a craft, an owner, two dates and
a status. Deliberately no amount anywhere on it - what a freelancer is
paid is a cost line on the deal and an expense on the job, and keeping
money off this doctype is what lets crew read it at all.

The crew boundary lives here rather than on Job because the founder's
standing rule is that a number they cannot see must be unreachable
through the document API, the list API *and* global search. Field-level
permissions would have to hold that line field by field across the whole
job - its carried breakdown, its packages, its quote totals, its
milestones, and every money endpoint that gates on Job read. So crew are
granted nothing at all on Job. They read the tasks, and a money-free
view of the job assembled by `auraos.api.crew_job`.

What a crew session may do here, enforced twice - once by the
`has_permission` hook (the document and list API) and once by
`guard_crew_edit` (the write itself):

- read every task on a job they hold a task on, so the board and the
  timeline show the whole plan and not only their own row
- move their own task's status, and add a note to it
- nothing else: not another person's task, not a task on a job they are
  not on, not a title, not a date, not a new task, not a deletion
"""

import frappe
from frappe import _
from frappe.model.document import Document

# The role a designer, editor or colourist holds. One role, not one per
# craft: the craft is a field on the task, so a new trade is a Desk
# entry rather than a new permission surface to prove blind twice over.
CREW_ROLE = "Crew"

# The board, in column order. Statuses are a fixed vocabulary because
# the columns of a kanban are its whole shape - a typed-in status would
# make a column appear out of a spelling mistake.
STATUSES = ("To do", "In progress", "Blocked", "In review", "Done")
DEFAULT_STATUS = STATUSES[0]
DONE = STATUSES[-1]

# What a crew session may change on its own task. Everything else on the
# task is the plan, and the plan belongs to whoever is running the job.
CREW_EDITABLE_FIELDS = ("status", "notes")

# The reading order of a job's tasks: dated work in date order, undated
# work after it, and creation order to break ties so the board never
# reshuffles itself between two loads.
ORDER_BY = (
    "ifnull(start_date, '2999-12-31') asc, "
    "ifnull(end_date, '2999-12-31') asc, creation asc"
)

TASK_FIELDS = (
    "name",
    "job",
    "title",
    "craft",
    "assigned_to",
    "start_date",
    "end_date",
    "status",
    "notes",
)


def holds_crew_role(user):
    # Explicit assignments only - frappe.get_roles reports every role
    # for Administrator, which would file the founder under crew.
    return bool(frappe.db.exists("Has Role", {"parent": user, "role": CREW_ROLE}))


def is_crew_only(user=None):
    """True for a session that is crew and nothing else.

    Someone holding both Crew and an operating role is not crew for
    permission purposes - a producer who also edits is still a producer.
    """
    from auraos.auraos.doctype.deal.deal import holds_operating_role

    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return False
    return holds_crew_role(user) and not holds_operating_role(user)


def crew_job_names(user=None):
    """The jobs a crew member is on: the ones they hold a task on.

    This is the whole of their reach. A job they hold no task on is not
    in their list, not in their search, and not readable by name.
    """
    user = user or frappe.session.user
    return frappe.get_all(
        "Job Task",
        filters={"assigned_to": user},
        pluck="job",
        distinct=True,
    )


def may_read_job_tasks(job, user=None):
    """Whether this session may see the task plan of a job.

    Two doors, and they are different doors: an operating role reads the
    job itself, crew read only the plan of a job they are on.
    """
    user = user or frappe.session.user
    if is_crew_only(user):
        return job in crew_job_names(user)
    return frappe.has_permission("Job", "read", doc=job, user=user)


def tasks_for_job(job):
    """Every task on a job, in reading order.

    Read with get_all, which skips row-level permissions: the caller's
    check on the job is the entire authorization for these rows.
    """
    return frappe.get_all(
        "Job Task",
        filters={"job": job},
        fields=list(TASK_FIELDS),
        order_by=ORDER_BY,
        limit_page_length=0,
    )


# -- the permission hooks (hooks.py) --


def has_permission(doc, ptype="read", user=None, **kwargs):
    """Document-level gate for a crew session.

    Returning True is not a grant - Frappe still requires the role
    permission on the doctype. This only ever takes access away.

    The spare kwargs absorb whatever else the framework passes a
    permission hook (it has grown a `debug` argument since v15): a hook
    that raises a TypeError would deny nothing, it would break the page.
    """
    user = user or frappe.session.user
    if not is_crew_only(user):
        return True
    if ptype == "read":
        return doc.get("job") in crew_job_names(user)
    if ptype == "write":
        return doc.get("assigned_to") == user
    # Create, delete, submit, share, export: never.
    return False


def get_permission_query_conditions(user=None, doctype=None, **kwargs):
    """List-level gate: a crew list holds only the jobs they are on.

    Frappe passes the user positionally and the doctype by keyword; both
    are taken loosely for the same reason as `has_permission` above.
    """
    user = user or frappe.session.user
    if not is_crew_only(user):
        return ""
    names = crew_job_names(user)
    if not names:
        # No task, no jobs - and an empty IN () is a SQL syntax error.
        return "1=0"
    allowed = ", ".join(frappe.db.escape(name) for name in names)
    return f"`tabJob Task`.`job` in ({allowed})"


class JobTask(Document):
    def before_validate(self):
        if not self.status:
            self.status = DEFAULT_STATUS

    def validate(self):
        self.validate_title()
        self.validate_dates()
        self.guard_crew_edit()

    def validate_title(self):
        self.title = (self.title or "").strip()
        if not self.title:
            frappe.throw(_("A task needs a title"), frappe.ValidationError)

    def validate_dates(self):
        """A task may be undated, or dated one way round only.

        Undated is allowed on purpose: work gets written down before it
        gets scheduled, and a task nobody has dated yet still belongs on
        the board. It simply has no bar on the timeline.
        """
        if not (self.start_date and self.end_date):
            return
        if frappe.utils.getdate(self.end_date) < frappe.utils.getdate(self.start_date):
            frappe.throw(
                _("A task cannot be due before it starts"), frappe.ValidationError
            )

    def guard_crew_edit(self):
        """A crew session may move its own task, and change nothing else.

        The `has_permission` hook has already established that a crew
        writer owns this task. What is left is *what* they may write,
        which no role permission can express: status and notes, never
        the plan around them.
        """
        if not is_crew_only(frappe.session.user):
            return
        before = self.get_doc_before_save()
        if not before:
            frappe.throw(
                _("Tasks are planned by whoever is running the job"),
                frappe.PermissionError,
            )
        for field in self.meta.fields:
            if field.fieldtype in frappe.model.no_value_fields:
                continue
            if field.fieldname in CREW_EDITABLE_FIELDS:
                continue
            if self.get(field.fieldname) != before.get(field.fieldname):
                frappe.throw(
                    _("{0} on a task is set by whoever is running the job").format(
                        _(self.meta.get_label(field.fieldname))
                    ),
                    frappe.PermissionError,
                )
