"""Company identity on a quote, framework-free (T6.1a, issue #42).

A client-facing quote that says nothing about who is offering it cannot
be printed and attached to a contract. Putting the company on it means
reading a *second* document into a guest render context - AuraOS
Settings, which also holds the margin floor. So the identity travels the
same way the quote does: a named whitelist, not a blocklist.

Three things are pinned here, all provable without Frappe:

1. **The second guest boundary.** `company_view` copies the named fields
   and nothing else. A future setting is invisible to clients until
   someone adds it here on purpose - and the margin floor never is.
2. **Empty means absent.** An unfilled field comes back None so the
   template can drop the line entirely, rather than printing a label
   with a blank beside it. A bank block with nothing in it prints no
   heading at all.
3. **The document has a name.** A quote number carries its version, so
   a printed page can be matched to the record it came from.

Runs anywhere: pytest, no Frappe.
"""

import pytest

from auraos.lib.quote import (
    COMPANY_FIELDS,
    company_view,
    quote_number,
)


def settings(**overrides):
    """An AuraOS Settings row as the Single actually comes back.

    Internal settings included on purpose: this is the document the
    whitelist exists to stand between.
    """
    row = {
        "company_name": "Aura Productions",
        "logo": "/files/aura-logo.png",
        "tax_code": "0312345678",
        "address": "12 Nguyễn Huệ, Quận 1, TP.HCM",
        "phone": "028 3822 1234",
        "email": "hello@aura.example",
        "website": "aura.example",
        "bank_name": "Vietcombank",
        "bank_account_number": "0071000123456",
        "bank_account_name": "CONG TY TNHH AURA",
        "signatory_name": "Nguyễn Anh Chung",
        "signatory_title": "Giám đốc",
        # Not identity. The reason this file exists.
        "margin_floor_pct": 22.5,
        "quote_silence_days": 5,
    }
    row.update(overrides)
    return row


# -- the second guest boundary --


BLOCK_FLAGS = {"has_bank", "has_contact", "has_letterhead"}


def test_company_view_keeps_only_whitelisted_fields():
    view = company_view(settings())
    assert set(view) == set(COMPANY_FIELDS) | BLOCK_FLAGS


@pytest.mark.parametrize(
    "internal", ["margin_floor_pct", "quote_silence_days", "payment_terms_days"]
)
def test_company_view_drops_every_internal_setting(internal):
    """The margin floor is one typo away from a client's page. Not today."""
    assert internal not in company_view(settings())


def test_company_view_never_leaks_a_setting_added_later():
    view = company_view(settings(overhead_per_month=80_000_000))
    assert "overhead_per_month" not in view


def test_company_view_survives_a_settings_row_with_nothing_on_it():
    """A site that never filled the block in still renders a page."""
    view = company_view({})
    assert set(view) == set(COMPANY_FIELDS) | BLOCK_FLAGS
    assert all(view[field] is None for field in COMPANY_FIELDS)
    assert view["has_letterhead"] is False


def test_company_view_carries_the_identity_a_client_reads():
    view = company_view(settings())
    assert view["company_name"] == "Aura Productions"
    assert view["tax_code"] == "0312345678"
    assert view["logo"] == "/files/aura-logo.png"
    assert view["signatory_title"] == "Giám đốc"


# -- empty means absent, not a blank beside a label --


def test_an_unfilled_field_is_none_rather_than_an_empty_string():
    """The template drops a line on None; "" would print the label."""
    view = company_view(settings(website="", phone=None))
    assert view["website"] is None
    assert view["phone"] is None


def test_the_bank_block_is_absent_when_nothing_is_filled_in():
    view = company_view(
        settings(bank_name="", bank_account_number="", bank_account_name="")
    )
    assert view["has_bank"] is False


def test_one_bank_field_is_enough_to_print_the_block():
    """Half a bank block still tells a client where to pay."""
    view = company_view(
        settings(bank_name="", bank_account_name="", bank_account_number="0071000")
    )
    assert view["has_bank"] is True


def test_the_contact_block_is_absent_when_nothing_is_filled_in():
    view = company_view(settings(phone="", email="", website="", address=""))
    assert view["has_contact"] is False


def test_an_address_alone_is_a_contact_block():
    view = company_view(settings(phone="", email="", website=""))
    assert view["has_contact"] is True


def test_the_tax_code_does_not_count_as_contact_details():
    """It sits in the letterhead's identity line, not the contact block."""
    view = company_view(settings(phone="", email="", website="", address=""))
    assert view["tax_code"] == "0312345678"
    assert view["has_contact"] is False


def test_a_letterhead_survives_a_missing_company_name():
    """Per field, not all-or-nothing.

    Gating the whole letterhead on the name would drop a filled tax code
    and address off the page - the opposite of the rule that an unfilled
    field prints nothing.
    """
    view = company_view(settings(company_name="", logo=""))
    assert view["has_letterhead"] is True


def test_contact_details_alone_are_a_letterhead():
    view = company_view(settings(company_name="", logo="", tax_code=""))
    assert view["has_letterhead"] is True


def test_a_signatory_alone_is_not_a_letterhead():
    """Those two belong to the PDF's signature block, not the masthead."""
    view = company_view(
        {"signatory_name": "Nguyễn Anh Chung", "signatory_title": "Giám đốc"}
    )
    assert view["has_letterhead"] is False


# -- the document's own name --


def test_a_quote_number_carries_its_version():
    assert quote_number("DQ-0007", 2) == "DQ-0007-v2"


def test_the_first_version_is_numbered_like_any_other():
    """v1 is written out. "DQ-0007" alone would be ambiguous once v2 exists."""
    assert quote_number("DQ-0007", 1) == "DQ-0007-v1"


def test_a_quote_number_without_a_version_is_just_the_record():
    assert quote_number("DQ-0007", None) == "DQ-0007"


def test_a_quote_number_with_no_record_is_nothing_at_all():
    assert quote_number(None, 2) is None
