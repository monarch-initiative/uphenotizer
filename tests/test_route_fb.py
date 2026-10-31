from pathlib import Path

import pytest
import yaml

from uphenotizer.model import COVERED_UPSTREAM, ROUTED, SKIPPED, UNROUTED, Route, Unit
from uphenotizer.obo import Term
from uphenotizer.route_fb import FlybaseRouter

CONFIG = yaml.safe_load((Path(__file__).parents[1] / "config/flybase.yaml").read_text())

FBCV = {
    "FBcv:0000351": Term("FBcv:0000351", "lethal", "phenotypic_class"),
    "FBcv:0000335": Term("FBcv:0000335", "germline clone", "clone_qualifier"),
    "FBcv:0000298": Term("FBcv:0000298", "recessive", "dominance_qualifier"),
    "FBcv:0000068": Term("FBcv:0000068", "increased number", "structural_qualifier"),
    "FBcv:0007048": Term("FBcv:0007048", "decreased number", "structural_qualifier"),
    "FBcv:0000059": Term("FBcv:0000059", "dorsal", "spatial_qualifier"),
}
GO = {
    "GO:0000001": Term("GO:0000001", "bp", "biological_process"),
    "GO:0000002": Term("GO:0000002", "cc", "cellular_component"),
    "GO:0000003": Term("GO:0000003", "mf", "molecular_function"),
    "GO:0000004": Term("GO:0000004", "old", "biological_process", obsolete=True),
}


@pytest.fixture
def router():
    return FlybaseRouter(CONFIG, FBCV, GO)


def route(router, *terms):
    return router.route(Unit("FB", tuple(terms)))


def test_empty_skipped(router):
    assert route(router).status == SKIPPED


def test_dpo_head_covered_upstream(router):
    assert route(router, "FBcv:0000351", "FBcv:0000298").status == COVERED_UPSTREAM


def test_clone_head_unrouted(router):
    assert route(router, "FBcv:0000335").status == UNROUTED


def test_anatomy_drops_context_and_stage(router):
    o = route(router, "FBbt:00004729", "FBcv:0000298", "FBdv:00005369")
    assert o.status == ROUTED
    assert o.route == Route.of("abnormalAnatomicalEntity", anatomical_entity="FBbt:00004729")


@pytest.mark.parametrize("modifier,pattern", [
    ("FBcv:0000068", "abnormallyIncreasedNumberOfAnatomicalEntity"),
    ("FBcv:0007048", "abnormallyDecreasedNumberOfAnatomicalEntity"),
])
def test_anatomy_number_modifiers(router, modifier, pattern):
    o = route(router, "FBbt:00004729", modifier, "FBcv:0000335")
    assert o.route == Route.of(pattern, anatomical_entity="FBbt:00004729")


def test_spatial_qualifier_blocks(router):
    o = route(router, "FBbt:00004729", "FBcv:0000059")
    assert o.status == UNROUTED
    assert "FBcv:0000059" in o.reason


def test_two_modifiers_unrouted(router):
    assert route(router, "FBbt:1", "FBcv:0000068", "FBcv:0007048").status == UNROUTED


@pytest.mark.parametrize("go,pattern,var", [
    ("GO:0000001", "abnormalBiologicalProcess", "biological_process"),
    ("GO:0000002", "abnormalCellularComponent", "cellular_component"),
    ("GO:0000003", "abnormalMolecularFunction", "molecular_function"),
])
def test_go_by_namespace(router, go, pattern, var):
    assert route(router, go, "FBcv:0000298").route == Route.of(pattern, **{var: go})


def test_obsolete_or_unknown_go_unrouted(router):
    assert route(router, "GO:0000004").status == UNROUTED
    assert route(router, "GO:9999999").status == UNROUTED


def test_go_with_modifier_unrouted(router):
    assert route(router, "GO:0000001", "FBcv:0000068").status == UNROUTED


def test_configured_patterns(router):
    pats = router.configured_patterns()
    assert pats["abnormalAnatomicalEntity"] == ["anatomical_entity"]
    assert pats["abnormalMolecularFunction"] == ["molecular_function"]
