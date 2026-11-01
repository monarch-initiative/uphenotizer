import pytest

from uphenotizer.components import COMPONENTS
from uphenotizer.idmap import ComponentIdMap

DPO = COMPONENTS["FB"]
APO = COMPONENTS["SGD"]
BASE = "https://w3id.org/monarch-initiative/entity/PHENOTYPE_"


def test_mint_starts_at_range_and_is_padded(tmp_path):
    m = ComponentIdMap(DPO, tmp_path / "dpo-ext.tsv")
    assert m.update({"FBbt:2-P", "FBbt:1-P"})["minted"] == 2
    assert m.iri("FBbt:1-P") == BASE + "1000000"
    assert m.rows["FBbt:2-P"]["id"] == "PHENOTYPE:1000001"


def test_components_never_collide(tmp_path):
    d = ComponentIdMap(DPO, tmp_path / "d.tsv")
    a = ComponentIdMap(APO, tmp_path / "a.tsv")
    d.update({"K-P"})
    a.update({"K-P"})  # same key in both components -> two different classes
    assert d.iri("K-P") != a.iri("K-P")
    assert DPO.first <= int(d.iri("K-P")[len(BASE):]) <= DPO.last
    assert APO.first <= int(a.iri("K-P")[len(BASE):]) <= APO.last


def test_range_enforced():
    with pytest.raises(ValueError):
        DPO.iri(2000000)


def test_unused_keys_keep_their_class_and_ids_are_never_reused(tmp_path):
    p = tmp_path / "dpo-ext.tsv"
    m = ComponentIdMap(DPO, p)
    m.update({"A-P", "B-P"})
    m.save()
    m2 = ComponentIdMap(DPO, p)
    assert m2.update({"B-P", "C-P"}) == {"minted": 1, "unused": 1}
    assert [k for k, _ in m2.items()] == ["A-P", "B-P", "C-P"]  # A is still released
    assert m2.rows["C-P"]["id"] == "PHENOTYPE:1000002"


def test_reading_old_maps_with_status_column(tmp_path):
    p = tmp_path / "x.tsv"
    p.write_text("id\tkey\tstatus\nPHENOTYPE:1000000\tA-P\tdeprecated\n")
    m = ComponentIdMap(DPO, p)
    m.save()
    assert p.read_text() == "id\tkey\nPHENOTYPE:1000000\tA-P\n"


def test_items_ordered_by_id(tmp_path):
    m = ComponentIdMap(DPO, tmp_path / "x.tsv")
    m.update({"Z-P"})
    m.update({"Z-P", "A-P"})
    assert [k for k, _ in m.items()] == ["Z-P", "A-P"]


def test_file_iri():
    assert DPO.file_iri("base.owl") == \
        "https://w3id.org/monarch-initiative/uphenotizer/release/dpo-ext-base.owl"
