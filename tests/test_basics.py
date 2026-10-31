import pytest

from uphenotizer.curie import expand, is_curie
from uphenotizer.obo import load_obo


def test_expand():
    assert expand("GO:0008150") == "http://purl.obolibrary.org/obo/GO_0008150"
    assert expand("FBbt:00004729") == "http://purl.obolibrary.org/obo/FBbt_00004729"


def test_expand_rejects_iri():
    with pytest.raises(ValueError):
        expand("http://purl.obolibrary.org/obo/GO_0008150")


def test_is_curie():
    assert is_curie("APO:0000003")
    assert not is_curie("not a curie")
    assert not is_curie("")


def test_load_obo(tmp_path):
    obo = tmp_path / "x.obo"
    obo.write_text(
        "format-version: 1.2\n\n"
        "[Term]\nid: FBcv:0000298\nname: recessive\nnamespace: dominance_qualifier\n\n"
        "[Term]\nid: GO:0000001\nname: old\nnamespace: biological_process\nis_obsolete: true\n\n"
        "[Typedef]\nid: part_of\nname: part of\n"
    )
    terms = load_obo(obo)
    assert set(terms) == {"FBcv:0000298", "GO:0000001"}
    assert terms["FBcv:0000298"].namespace == "dominance_qualifier"
    assert terms["GO:0000001"].obsolete
