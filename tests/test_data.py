"""The synthetic data files load cleanly and hang together."""

from pulse import data


def test_every_update_belongs_to_a_known_program(programs, updates):
    assert {u.program_id for u in updates} <= set(programs)


def test_update_ids_are_unique(updates):
    assert len({u.id for u in updates}) == len(updates)


def test_demo_outputs_cover_every_latest_update(updates, analyses):
    latest = data.latest_update_per_program(updates)
    assert {u.id for u in latest.values()} == set(analyses)


def test_brief_items_point_at_real_programs(programs):
    brief = data.load_demo_brief()
    for item in brief.items:
        assert item.program_ids and set(item.program_ids) <= set(programs)


def test_assessment_changes_are_computed():
    df = data.load_assessments().dropna(subset=["mold_after"])
    assert (df["mold_change_pct"] < 0).all()


def test_demo_data_tells_the_honest_product_story():
    """In-duct units barely move particles; neither product moves CO2."""
    df = data.load_assessments().dropna(subset=["mold_after"])
    by = df.groupby("solution").median(numeric_only=True)
    assert by.loc["Portable", "pm25_change_pct"] < -50
    assert by.loc["In-duct", "pm25_change_pct"] > -20
    assert df["co2_change_pct"].abs().max() < 5
