import csv

import pytest

from uphenotizer.model import COVERED_UPSTREAM, PENDING, ROUTED, UNROUTED, Outcome, Route, Unit
from uphenotizer.upheno import UphenoIdMap, UphenoSource
from uphenotizer.write import ConfigError, validate_patterns, write_outputs

UP = "http://purl.obolibrary.org/obo/"
DEC_RES = "abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity"


def read(path):
    with open(path) as f:
        return list(csv.reader(f, delimiter="\t"))


def routed(pattern, n=1, chemical=None, **fillers):
    return Outcome(Unit("SGD", ("APO:0000003", "APO:0000087"), chemical, n, "stmt"), ROUTED,
                   rule="r", route=Route.of(pattern, **fillers))


def test_validate_missing_pattern(catalog):
    with pytest.raises(ConfigError, match="doesNotExist"):
        validate_patterns({"doesNotExist": ["x"]}, catalog)


def test_validate_var_mismatch(catalog):
    with pytest.raises(ConfigError, match="abnormalBiologicalProcess"):
        validate_patterns({"abnormalBiologicalProcess": ["chemical_entity"]}, catalog)


def test_validate_ok(catalog):
    validate_patterns({"abnormalAnatomicalEntity": ["anatomical_entity"],
                       "localOnlyPattern": ["x"]}, catalog)


@pytest.fixture
def written(catalog, upheno_dir, tmp_path):
    out = tmp_path / "out"
    (out / "patterns").mkdir(parents=True)
    (out / "patterns" / "stale.tsv").write_text("x\n")
    outcomes = [
        routed(DEC_RES, 5, "CHEBI:1", chemical_entity="CHEBI:1"),
        routed(DEC_RES, 3, "CHEBI:9", chemical_entity="CHEBI:9"),
        routed(DEC_RES, 1, "CHEBI:9", chemical_entity="CHEBI:9"),  # duplicate row
        routed("localOnlyPattern", 2, x="GO:0000001"),
        routed(DEC_RES, 1, "bad id", chemical_entity="bad id"),
        Outcome(Unit("FB", ("FBcv:0000351",), None, 40, "lethal"), COVERED_UPSTREAM),
        Outcome(Unit("SGD", ("APO:0000003", "APO:0000110"), "CHEBI:1", 7, "dcf"), UNROUTED,
                reason="no rule"),
        Outcome(Unit("SGD", ("APO:0000003", "APO:0000110"), None, 4, "dcf"), UNROUTED,
                reason="no rule"),
    ]
    summary = write_outputs(outcomes, catalog, UphenoIdMap.from_source(UphenoSource(upheno_dir)), out)
    return out, outcomes, summary


def test_pattern_table_shape_and_reuse(written):
    out, _, _ = written
    rows = read(out / "patterns" / f"{DEC_RES}.tsv")
    assert rows[0] == ["chemical_entity", "defined_class"]
    assert rows[1:] == [[f"{UP}CHEBI_1", f"{UP}UPHENO_0000001"], [f"{UP}CHEBI_9", ""]]


def test_stale_tables_removed(written):
    out, _, _ = written
    assert not (out / "patterns" / "stale.tsv").exists()


def test_local_pattern_goes_to_pending(written):
    out, outcomes, _ = written
    assert outcomes[3].status == PENDING
    assert read(out / "pending" / "localOnlyPattern.tsv")[1] == [f"{UP}GO_0000001", ""]
    assert not (out / "patterns" / "localOnlyPattern.tsv").exists()


def test_malformed_filler_unrouted(written):
    _, outcomes, _ = written
    assert outcomes[4].status == UNROUTED
    assert "bad id" in outcomes[4].reason


def test_source_map_has_key_and_sorted(written):
    out, _, _ = written
    rows = read(out / "source_map.tsv")
    assert rows[0][:4] == ["source", "source_terms", "chemical", "annotations"]
    assert rows[1][0] == "FB"
    sgd = [r for r in rows[1:] if r[0] == "SGD"]
    assert [int(r[3]) for r in sgd] == sorted((int(r[3]) for r in sgd), reverse=True)
    assert rows[0][8:11] == ["key", "class_id", "upheno_id"]
    first = next(r for r in rows if r[2] == "CHEBI:1" and r[5] == "routed")
    assert first[8] == f"CHEBI:1-{DEC_RES}"
    assert first[10] == f"{UP}UPHENO_0000001"


def test_unrouted_grouped_over_chemicals(written):
    out, _, _ = written
    rows = read(out / "unrouted.tsv")
    no_rule = [r for r in rows[1:] if r[5] == "no rule"]
    assert no_rule == [["SGD", "APO:0000003|APO:0000110", "11", "1", "dcf", "no rule"]]


def test_summary_counts(written):
    _, _, summary = written
    assert f"| {DEC_RES} | 2 | 1 | 1 | 0 |" in summary
    assert "| localOnlyPattern | 1 | 0 | 0 | 1 |" in summary
    assert "| FB | covered_upstream | 1 | 40 | 100.0% |" in summary
