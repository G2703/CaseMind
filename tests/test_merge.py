import pytest

from ontology_schema import OntologyManager


def test_merge_simple():
    om = OntologyManager()
    base = {
        "nodes": [
            {
                "name": "Robbery",
                "attributes": {"weapon_used": ["knife"], "location": ["market"]},
                "synonyms": ["theft"],
            }
        ]
    }

    new = {
        "nodes": [
            {
                "name": "Robbery",
                "attributes": {"weapon_used": ["pistol"], "victim_age": ["adult"]},
                "synonyms": ["robbery"],
            },
            {
                "name": "Assault",
                "attributes": {"weapon_used": ["fist"]},
            },
        ]
    }

    merged = om.merge_ontologies(base, new)
    names = {n["name"] for n in merged["nodes"]}
    assert "Robbery" in names
    assert "Assault" in names

    # find Robbery node
    rnode = next(n for n in merged["nodes"] if n["name"] == "Robbery")
    # weapon_used should contain both
    assert set(rnode["attributes"].get("weapon_used", [])) == {"knife", "pistol"}
    # victim_age should be present
    assert "victim_age" in rnode["attributes"]


def test_validate_duplicate_names():
    om = OntologyManager()
    ont = {"nodes": [{"name": "Robbery"}, {"name": "robbery"}]}
    errs = om.validate_ontology(ont)
    assert any("duplicate node name" in e for e in errs)
