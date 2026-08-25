"""Pure-python tests for auraos.lib.paper_status - no Frappe required.

Issue #106. Three things are rules rather than plumbing, so they are
pinned here rather than only in the Frappe-side test:

- **The vocabulary is exactly three words**, spelled one way. A screen
  that invents a fourth, or a caller that sends "signed", is refused.
- **Nothing enforces an order.** Every move between the three is legal,
  Signed back to Draft included, because a real document sometimes has
  to be redone.
- **A blank reads as Draft**, which is how papers generated before the
  field existed stay out of the "still unsigned" answer's way.

The Frappe-side test (auraos/auraos/doctype/generated_paper/
test_generated_paper.py) proves the doctype and the API go through this.
"""

from itertools import product

import pytest

from auraos.lib.paper_status import (
    AWAITING_SIGNATURE,
    DRAFT,
    SIGNED,
    STATUSES,
    can_move,
    is_status,
    status_or_draft,
    validated,
)


# -- the vocabulary --


def test_the_three_states_a_paper_can_be_in():
    assert STATUSES == (DRAFT, AWAITING_SIGNATURE, SIGNED)
    assert (DRAFT, AWAITING_SIGNATURE, SIGNED) == ("Draft", "Awaiting signature", "Signed")


@pytest.mark.parametrize("status", STATUSES)
def test_each_of_the_three_is_a_status(status):
    assert is_status(status)
    assert validated(status) == status


@pytest.mark.parametrize("value", ["signed", "SIGNED", "Sent", "", None, 0, "Awaiting Signature"])
def test_anything_else_is_not(value):
    assert not is_status(value)
    with pytest.raises(ValueError):
        validated(value)


def test_the_refusal_names_what_was_allowed():
    """The API repeats this sentence to whoever typed the wrong word."""
    with pytest.raises(ValueError) as refused:
        validated("Posted")

    assert "Draft, Awaiting signature, Signed" in str(refused.value)


# -- no order is enforced --


@pytest.mark.parametrize("current,target", list(product(STATUSES, STATUSES)))
def test_any_status_may_follow_any_other(current, target):
    """Including Signed back to Draft: a paper sometimes has to be redone."""
    assert can_move(current, target)


def test_a_paper_may_be_moved_back_to_draft():
    assert can_move(SIGNED, DRAFT)
    assert can_move(AWAITING_SIGNATURE, DRAFT)


def test_moving_a_paper_to_the_status_it_already_has_is_allowed():
    assert can_move(SIGNED, SIGNED)


@pytest.mark.parametrize("target", ["Sent", "", None])
def test_nothing_outside_the_vocabulary_may_be_moved_to(target):
    assert not can_move(DRAFT, target)


def test_a_paper_whose_stored_status_is_nonsense_cannot_be_moved():
    assert not can_move("Posted", SIGNED)


# -- what an older row reads as --


@pytest.mark.parametrize("stored", [None, "", "   "])
def test_a_paper_written_before_the_field_existed_reads_as_draft(stored):
    assert status_or_draft(stored) == DRAFT


@pytest.mark.parametrize("stored", STATUSES)
def test_a_stored_status_reads_as_itself(stored):
    assert status_or_draft(stored) == stored


def test_a_stored_value_that_is_not_blank_and_not_a_status_is_still_an_error():
    """Only the blank is forgiven - nonsense stays visible."""
    with pytest.raises(ValueError):
        status_or_draft("Posted")
