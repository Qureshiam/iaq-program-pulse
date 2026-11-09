"""The grounding check catches quotes that are not really in the source."""

from pulse.grounding import all_grounded, check_analysis, is_grounded

SOURCE = "Shipment still held at customs.  New certificate expected Oct 20. Need approval by Oct 19."


def test_exact_quote_is_grounded():
    assert is_grounded("New certificate expected Oct 20", SOURCE)


def test_case_spacing_and_trailing_punctuation_are_ignored():
    assert is_grounded("  shipment STILL held at   customs.", SOURCE)


def test_smart_quotes_match_plain_quotes():
    assert is_grounded("the school’s landlord", "a permit from the school's landlord")


def test_made_up_quote_is_not_grounded():
    assert not is_grounded("Shipment released from customs", SOURCE)


def test_very_short_quote_proves_nothing():
    assert not is_grounded("Oct", SOURCE)


def test_demo_data_has_exactly_one_planted_hallucination(updates, analyses):
    by_id = {u.id: u for u in updates}
    failures = {
        uid: [c.item for c in check_analysis(a, by_id[uid].text) if not c.grounded]
        for uid, a in analyses.items()
        if not all_grounded(a, by_id[uid].text)
    }
    assert failures == {"INV-2026-10-15": ["risk 2"]}
