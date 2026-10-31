"""Annotations are re-bound every run: when the export gains a chemical, the binding moves from the
generic fallback class to the specific class, and an unused fallback class is deprecated."""

from pathlib import Path

from uphenotizer.alliance import units_sgd
from uphenotizer.dosdp_tables import bind, update_idmaps
from uphenotizer.model import ROUTED
from uphenotizer.route_sgd import SgdRouter, load_rules, read_tsv
from uphenotizer.upheno import UphenoIdMap, UphenoSource
from uphenotizer.write import finalize

ROOT = Path(__file__).parents[1]
DEC_RES = "abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity"


def record(chemical=None):
    r = {"phenotypeStatement": "decreased resistance to chemicals",
         "phenotypeTermIdentifiers": [{"termId": "APO:0000003", "termOrder": 1},
                                      {"termId": "APO:0000087", "termOrder": 2}]}
    if chemical:
        r["conditionRelations"] = [{"conditions": [
            {"chemicalOntologyId": chemical, "conditionClassId": "ZECO:0000111"}]}]
    return r


def run(records, catalog, upheno_dir, idmaps):
    router = SgdRouter(load_rules(ROOT / "config/sgd_rules.tsv"),
                       {r["qualifier"] for r in read_tsv(ROOT / "config/sgd_skip.tsv")}, {}, {})
    outcomes = [router.route(u) for u in units_sgd(records)]
    finalize(outcomes, catalog, UphenoIdMap.from_source(UphenoSource(upheno_dir)))
    maps = update_idmaps(outcomes, idmaps, {"SGD"})
    bind(outcomes, maps)
    return outcomes, maps["SGD"]


def test_fallback_is_marked(catalog, upheno_dir, tmp_path):
    outcomes, _ = run([record()], catalog, upheno_dir, tmp_path / "idmaps")
    (o,) = outcomes
    assert o.status == ROUTED and o.extra["fallback"]
    assert o.extra["key"] == f"CHEBI:24431-{DEC_RES}"
    assert o.reason.startswith("fallback CHEBI:24431")


def test_rebinding_when_chemical_appears(catalog, upheno_dir, tmp_path):
    idmaps = tmp_path / "idmaps"
    week1, _m1 = run([record()], catalog, upheno_dir, idmaps)
    generic_id = week1[0].extra["class_id"]

    week2, m2 = run([record("CHEBI:29699")], catalog, upheno_dir, idmaps)
    (o,) = week2
    assert "fallback" not in o.extra
    assert o.extra["key"] == f"CHEBI:29699-{DEC_RES}"
    assert o.extra["class_id"] != generic_id                       # re-bound to the specific class
    assert m2.rows[f"CHEBI:24431-{DEC_RES}"]["status"] == "deprecated"  # nothing binds to it anymore
    assert m2.rows[f"CHEBI:24431-{DEC_RES}"]["id"] == generic_id    # ID kept, never reused


def test_generic_class_stays_while_some_records_lack_chemical(catalog, upheno_dir, tmp_path):
    idmaps = tmp_path / "idmaps"
    run([record(), record()], catalog, upheno_dir, idmaps)
    week2, m = run([record("CHEBI:29699"), record()], catalog, upheno_dir, idmaps)
    assert {o.extra["key"] for o in week2} == {f"CHEBI:29699-{DEC_RES}", f"CHEBI:24431-{DEC_RES}"}
    assert m.rows[f"CHEBI:24431-{DEC_RES}"]["status"] == "active"
