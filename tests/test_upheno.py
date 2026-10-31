from uphenotizer.upheno import UphenoIdMap, UphenoSource, make_key, upheno_key

UP = "http://purl.obolibrary.org/obo/"


def test_make_key_single():
    assert make_key({"chemical_entity": "CHEBI:1"}, "P") == "CHEBI:1-P"


def test_make_key_sorted_by_var_name():
    assert make_key({"location": "UBERON:2", "anatomical_entity": "FBbt:1"}, "P") == \
        "FBbt:1-UBERON:2-P"


def test_upheno_key_matches_upheno_id_map_shape():
    assert upheno_key({"biological_process": "GO:0000010"}, "abnormalBiologicalProcess") == \
        f"{UP}GO_0000010-abnormalBiologicalProcess.tsv"


def test_catalog_resolves_dosdp_dev_and_local(catalog):
    assert catalog.vars("abnormalAnatomicalEntity") == ["anatomical_entity"]
    assert not catalog.is_local("abnormalAnatomicalEntity")
    assert catalog.vars("localOnlyPattern") == ["x"]
    assert catalog.is_local("localOnlyPattern")
    assert catalog.vars("doesNotExist") is None


def test_idmap_lookup_and_duplicates(upheno_dir):
    idmap = UphenoIdMap.from_source(UphenoSource(upheno_dir))
    pattern = "abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity"
    assert idmap.lookup({"chemical_entity": "CHEBI:1"}, pattern) == f"{UP}UPHENO_0000001"
    assert idmap.lookup({"chemical_entity": "CHEBI:9"}, pattern) is None
