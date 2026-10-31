import gzip
import json

from uphenotizer.alliance import load_records, ordered_terms, units_flybase, units_sgd


def rec(terms, statement="s", chems=()):
    r = {
        "phenotypeStatement": statement,
        "phenotypeTermIdentifiers": [{"termId": t, "termOrder": o} for t, o in terms],
    }
    if chems:
        r["conditionRelations"] = [
            {"conditions": [{"chemicalOntologyId": c, "conditionClassId": "ZECO:0000111"}
                            for c in chems]}
        ]
    return r


def test_ordered_terms_sorts_by_term_order_with_gaps():
    assert ordered_terms(rec([("B", 3), ("A", 1)])) == ("A", "B")


def test_flybase_aggregation_keeps_first_statement():
    units = units_flybase([rec([("FBbt:1", 1)], "first"), rec([("FBbt:1", 1)], "second")])
    assert len(units) == 1
    assert units[0].annotations == 2
    assert units[0].example_statement == "first"


def test_sgd_two_chemicals_give_two_units():
    r = rec([("APO:0000003", 1), ("APO:0000087", 2)], chems=["CHEBI:1", "CHEBI:2"])
    units = sorted(units_sgd([r, rec([("APO:0000003", 1), ("APO:0000087", 2)])]),
                   key=lambda u: str(u.chemical))
    assert [(u.chemical, u.annotations) for u in units] == [("CHEBI:1", 1), ("CHEBI:2", 1),
                                                            (None, 1)]


def test_unmapped_chemical_condition_kept():
    r = rec([("APO:0000003", 1), ("APO:0000087", 2)])
    r["conditionRelations"] = [{"conditions": [
        {"conditionClassId": "ZECO:0000111", "conditionStatement": "chemical:Polygodial"},
        {"conditionClassId": "ZECO:0000238", "conditionStatement": "media:YPD"},
    ]}]
    assert [u.chemical for u in units_sgd([r])] == ["unmapped:chemical:Polygodial"]


def test_load_records_gz(tmp_path):
    p = tmp_path / "x.json.gz"
    with gzip.open(p, "wt") as f:
        json.dump({"data": [rec([("FBbt:1", 1)])]}, f)
    assert len(load_records(p)) == 1
