from __future__ import annotations

from eden.semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE, extract_semantic_candidates


def test_extract_semantic_candidates_derives_typed_relations_and_entities() -> None:
    text = (
        'Michel Foucault wrote "The Archaeology of Knowledge". '
        "J. L. Austin authored How to Do Things with Words. "
        "Gilles Deleuze influenced Michel Foucault. "
        "The Archaeology of Knowledge references The Order of Things."
    )

    extracted = extract_semantic_candidates(text, limit=6)
    relation_types = {candidate["edge_type"] for candidate in extracted["relation_candidates"]}
    labels = {candidate["label"] for candidate in extracted["meme_candidates"]}

    assert "AUTHOR_OF" in relation_types
    assert "INFLUENCES" in relation_types
    assert "REFERENCES" in relation_types
    assert "Michel Foucault" in labels
    assert "The Archaeology of Knowledge" in labels
    assert MEMODE_MEMBERSHIP_EDGE_TYPE == "MEMODE_HAS_MEMBER"
