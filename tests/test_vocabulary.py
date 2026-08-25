"""Pure-python tests for auraos.lib.vocabulary - no Frappe required.

T3.5 / issue #29. Three decisions live in the pure module because each
is a rule rather than plumbing:

- **Who manages which list.** The walkthrough answer of 2026-08-10 gave
  deal sources to the producer as well - superseding the founder-only
  guard T3.2 built - and left project types with the founder and the
  admin seat. That split is asserted here from both sides: what each
  seat may do, and what it must not.
- **A rename never merges.** Renaming onto a value already in the list
  would rewrite the deals on the target, so it is refused.
- **A value in use is not removable.** With the count in the refusal,
  because that is the number the founder reads.

The Frappe-side tests (auraos/tests/test_vocabulary_api.py) prove the
endpoints actually go through these functions, and that the DocType
permissions agree with them.
"""

import pytest

from auraos.lib.vocabulary import (
    PROJECT_TYPE,
    SOURCE,
    VOCABULARIES,
    UnknownVocabulary,
    clean_value,
    manageable_keys,
    may_manage,
    removal_refusal,
    rename_refusal,
    vocabulary,
)

FOUNDER = ["Founder"]
PRODUCER = ["Producer"]
ADMIN = ["System Manager"]
CREW = ["Crew"]
NOBODY = []


# -- who manages which list --


@pytest.mark.parametrize("roles", [FOUNDER, PRODUCER, ADMIN])
def test_founder_producer_and_admin_manage_sources(roles):
    # The walkthrough answer that supersedes T3.2's founder-only guard.
    assert may_manage("source", roles) is True


@pytest.mark.parametrize("roles", [FOUNDER, ADMIN])
def test_founder_and_admin_manage_project_types(roles):
    assert may_manage("project_type", roles) is True


def test_producer_does_not_manage_project_types():
    # The half of the change that did *not* happen: the type list still
    # drifts at the founder's pace.
    assert may_manage("project_type", PRODUCER) is False


@pytest.mark.parametrize("roles", [CREW, NOBODY])
@pytest.mark.parametrize("key", list(VOCABULARIES))
def test_crew_and_role_less_sessions_manage_nothing(roles, key):
    assert may_manage(key, roles) is False


def test_administrator_counts_as_the_admin_seat():
    # Frappe does not always list System Manager among Administrator's
    # roles, and the founder's own answer names "admin accounts".
    assert may_manage("project_type", ["Administrator"]) is True


def test_manageable_keys_is_what_the_settings_screen_draws():
    assert manageable_keys(PRODUCER) == ("source",)
    assert manageable_keys(FOUNDER) == ("source", "project_type")
    assert manageable_keys(CREW) == ()


def test_unknown_list_is_refused_by_name():
    with pytest.raises(UnknownVocabulary):
        vocabulary("margin_floor")
    with pytest.raises(UnknownVocabulary):
        may_manage("margin_floor", FOUNDER)


def test_every_list_declares_where_its_values_are_used():
    # `used_by` is what makes "in use" a count rather than a guess; a
    # list without it would remove values deals still hold.
    for vocab in VOCABULARIES.values():
        assert vocab.used_by
        assert all(len(pair) == 2 for pair in vocab.used_by)


def test_tags_are_not_a_managed_list():
    # Open-creation for both operating roles, from the deal form - the
    # walkthrough confirmed it, so there is no settings section to grow.
    assert "tag" not in VOCABULARIES
    assert "deal_tag" not in VOCABULARIES


# -- what a typed value becomes --


def test_surrounding_whitespace_is_taken_off():
    assert clean_value("  TikTok ") == "TikTok"


def test_case_and_accents_are_left_as_typed():
    assert clean_value("Zalo") == "Zalo"
    assert clean_value("Hội chợ") == "Hội chợ"


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_an_empty_value_is_refused(raw):
    with pytest.raises(ValueError):
        clean_value(raw)


# -- rename: migrates, but never merges --


def test_renaming_to_a_free_name_is_allowed():
    assert rename_refusal(SOURCE, "Expo", "Trade show", ["Expo", "Zalo"]) is None


def test_renaming_onto_an_existing_value_is_refused():
    refusal = rename_refusal(SOURCE, "Expo", "Zalo", ["Expo", "Zalo"])
    assert refusal
    assert "Zalo" in refusal
    assert "merge" in refusal


def test_renaming_a_value_to_itself_is_a_no_op():
    assert rename_refusal(SOURCE, "Expo", "Expo", ["Expo"]) is None


# -- removal: refused while the value is in use --


def test_an_unused_value_can_be_removed():
    assert removal_refusal(SOURCE, "Expo", 0) is None


def test_a_value_in_use_is_refused_with_its_count():
    refusal = removal_refusal(SOURCE, "Zalo", 12)
    assert refusal
    assert "Zalo" in refusal
    assert "12 deals" in refusal
    # The refusal has to point somewhere: renaming is the migrating way
    # out, and it is the only one this screen offers.
    assert "Rename" in refusal


def test_the_refusal_counts_one_deal_in_the_singular():
    refusal = removal_refusal(PROJECT_TYPE, "Documentary", 1)
    assert "1 deal." in refusal or "1 deal " in refusal
    assert "1 deals" not in refusal
