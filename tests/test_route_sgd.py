from pathlib import Path

import pytest

from uphenotizer.model import ROUTED, SKIPPED, UNROUTED, Route, Unit
from uphenotizer.obo import Term
from uphenotizer.route_sgd import SgdRouter, load_exact_go, load_rules, read_tsv

ROOT = Path(__file__).parents[1]
DEC_RES = "abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity"
GO = {
    "GO:0000010": Term("GO:0000010", "some process", "biological_process"),
    "GO:0000020": Term("GO:0000020", "some function", "molecular_function"),
}


@pytest.fixture
def router(tmp_path):
    sssom = tmp_path / "apo_go.sssom.tsv"
    sssom.write_text(
        "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tcomment\n"
        "APO:1000001\tsome process\tskos:exactMatch\tGO:0000010\tx\t\n"
        "APO:1000002\tsome function\tskos:exactMatch\tGO:0000020\tx\t\n"
        "APO:1000003\tbroad\tskos:broadMatch\tGO:0000010\tx\t\n"
        # specific rule exists for APO:0000087, so the GO wildcard must not win
        "APO:0000087\tresistance to chemicals\tskos:exactMatch\tGO:0000010\tx\t\n"
    )
    rules = load_rules(ROOT / "config/sgd_rules.tsv")
    skip = {r["qualifier"] for r in read_tsv(ROOT / "config/sgd_skip.tsv")}
    return SgdRouter(rules, skip, load_exact_go(sssom), GO)


def route(router, *terms, chemical=None):
    return router.route(Unit("SGD", tuple(terms), chemical))


def test_resistance_with_chemical(router):
    o = route(router, "APO:0000003", "APO:0000087", chemical="CHEBI:29699")
    assert o.status == ROUTED
    assert o.route == Route.of(DEC_RES, chemical_entity="CHEBI:29699")


def test_resistance_without_chemical_uses_fallback(router):
    assert route(router, "APO:0000003", "APO:0000087").route == \
        Route.of(DEC_RES, chemical_entity="CHEBI:24431")


def test_unmapped_chemical_does_not_fall_back(router):
    o = route(router, "APO:0000003", "APO:0000087", chemical="unmapped:chemical:Polygodial")
    assert o.status == UNROUTED
    assert "Polygodial" in o.reason


def test_unmapped_chemical_ignored_by_go_rules(router):
    o = route(router, "APO:0000002", "APO:1000001", chemical="unmapped:chemical:x")
    assert o.status == ROUTED


def test_toxin_without_chemical_unrouted(router):
    assert route(router, "APO:0000003", "APO:0000215").status == UNROUTED


def test_go_wildcard(router):
    assert route(router, "APO:0000002", "APO:1000001").route == \
        Route.of("abnormalBiologicalProcess", biological_process="GO:0000010")


def test_go_wildcard_requires_biological_process(router):
    assert route(router, "APO:0000002", "APO:1000002").status == UNROUTED


def test_go_wildcard_ignores_broad_match(router):
    assert route(router, "APO:0000002", "APO:1000003").status == UNROUTED


def test_specific_rule_beats_wildcard(router):
    assert route(router, "APO:0000003", "APO:0000087").route.pattern == DEC_RES


def test_viable_skipped(router):
    assert route(router, "APO:0000113").status == SKIPPED


def test_single_abnormal_term_unrouted(router):
    assert route(router, "APO:0000112").status == UNROUTED


def test_unmapped_unrouted(router):
    assert route(router, "APO:0000003", "APO:0000110").status == UNROUTED
