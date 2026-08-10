import frappe
from frappe import _
from frappe.model.document import Document

# Only the two operating roles may own a deal; ownership is the
# explicit handover instrument between the founder and the producer.
OPERATING_ROLES = {"Founder", "Producer"}


def check_attachment_permission(doc, method=None):
    """doc_events hook on File: attaching to a Deal requires write
    permission on that deal.

    Core File permissions let any System User create files, so without
    this gate a role-less user could hang attachments on deals they
    cannot even read.
    """
    if doc.flags.ignore_permissions:
        return
    if doc.attached_to_doctype == "Deal":
        frappe.has_permission(
            "Deal", "write", doc=doc.attached_to_name, throw=True
        )


def holds_operating_role(user):
    # Explicit role assignments only — frappe.get_roles reports every
    # role for Administrator, which would let it slip through.
    return bool(
        frappe.db.exists(
            "Has Role",
            {"parent": user, "role": ["in", list(OPERATING_ROLES)]},
        )
    )


class Deal(Document):
    def before_validate(self):
        # A deal created by an operating user belongs to them unless
        # they hand it over explicitly.
        if not self.deal_owner and holds_operating_role(frappe.session.user):
            self.deal_owner = frappe.session.user

    def validate(self):
        self.validate_owner()
        self.validate_lost_reason()

    def validate_owner(self):
        if self.deal_owner and not holds_operating_role(self.deal_owner):
            frappe.throw(
                _("Deal owner must hold the Founder or Producer role"),
                frappe.ValidationError,
            )

    def validate_lost_reason(self):
        if self.stage == "Lost":
            if not self.lost_reason:
                frappe.throw(
                    _("Marking a deal Lost requires a lost reason"),
                    frappe.ValidationError,
                )
        else:
            # A revived deal is no longer lost; a stale reason would
            # poison the lost-reason statistics.
            self.lost_reason = None
            self.lost_note = None

    def before_save(self):
        # After validation, so a rejected transition is never logged.
        previous = self.get_doc_before_save()
        from_stage = previous.stage if previous else None
        if self.is_new() or from_stage != self.stage:
            self.append(
                "stage_history",
                {
                    "from_stage": from_stage,
                    "to_stage": self.stage,
                    "changed_on": frappe.utils.now_datetime(),
                    "changed_by": frappe.session.user,
                },
            )
