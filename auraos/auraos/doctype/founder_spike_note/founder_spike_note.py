"""Founder-only spike DocType.

Carries no business logic. It exists so the permission proof in
test_founder_spike_note.py runs against a real founder-only schema
before any sensitive data (overhead, commission) enters the system.
"""

from frappe.model.document import Document


class FounderSpikeNote(Document):
    pass
