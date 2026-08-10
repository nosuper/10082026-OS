import frappe
from frappe import _
from frappe.model.document import Document

# Freelancers are people by definition; the tag makes no sense on a
# company and the founder asked for it to be impossible.
ROLES_NOT_FOR_COMPANIES = ("Freelancer",)


class PartyCompany(Document):
    def validate(self):
        for row in self.role_tags:
            if row.party_role in ROLES_NOT_FOR_COMPANIES:
                frappe.throw(
                    _("A company cannot carry the {0} role tag").format(
                        row.party_role
                    )
                )
