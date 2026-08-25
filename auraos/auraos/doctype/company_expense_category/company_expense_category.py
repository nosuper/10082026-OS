"""The accountant's vocabulary for money that belongs to no job.

Deliberately **not** `Cost Item Category`, which is the quoting
vocabulary a breakdown line picks from (Crew, Location, Equipment). The
two lists read to different people for different purposes: one prices a
shoot, the other tells the accountant which line of the books a payment
belongs on - chi phí tiếp khách, mua sắm vật tư. Sharing one list would
put "chi phí tiếp khách" in a quote's package picker and "Crew" in a tax
return.

**No Producer row in the permissions**, like the record it categorises:
a category list is small, but reading it tells you what the company
spends money on.
"""

from frappe.model.document import Document


class CompanyExpenseCategory(Document):
    pass
