from uphenotizer.classify import Hierarchy, is_upheno

E = "https://w3id.org/monarch-initiative/entity/PHENOTYPE_"


def h_from(tmp_path, rows):
    p = tmp_path / "classified.tsv"
    p.write_text("ID\tLABEL\tSubClass Of\tEquivalent Class\n" +
                 "".join("\t".join(r) + "\n" for r in rows))
    return Hierarchy.from_export(p)


def test_parse_ignores_anonymous_and_thing(tmp_path):
    h = h_from(tmp_path, [
        [E + "1", "x", "BFO:0000051 some (PATO:1)|UPHENO:1|owl:Thing", "BFO:0000051 some (A)|UPHENO:9"],
    ])
    assert h.supers[E + "1"] == {"UPHENO:1"}
    assert h.equivs[E + "1"] == {"UPHENO:9"}
    assert h.labels[E + "1"] == "x"


def test_nearest_walks_through_non_targets_and_drops_redundant(tmp_path):
    # ext1 -> ZP:1 -> UPHENO:2 -> UPHENO:1 ; ext1 -> UPHENO:1 (redundant)
    h = h_from(tmp_path, [
        [E + "1", "", "ZP:1|UPHENO:1", ""],
        ["ZP:1", "", "UPHENO:2", ""],
        ["UPHENO:2", "", "UPHENO:1", ""],
    ])
    assert h.nearest(E + "1", is_upheno) == {"UPHENO:2"}


def test_nearest_uses_equivalents_of_intermediate_nodes(tmp_path):
    # ext1 -> FYPO:1 (== UPHENO:5) -> UPHENO:1 : the grouping is UPHENO:5, not UPHENO:1
    h = h_from(tmp_path, [
        [E + "1", "", "FYPO:1", ""],
        ["FYPO:1", "", "UPHENO:1", "UPHENO:5"],
        ["UPHENO:5", "", "UPHENO:1", "FYPO:1"],
    ])
    assert h.nearest(E + "1", is_upheno) == {"UPHENO:5"}


def test_nearest_in_component_through_upheno(tmp_path):
    # ext1 -> UPHENO:3 -> ext2 : ext2 is ext1's nearest in-component parent
    h = h_from(tmp_path, [
        [E + "1", "", "UPHENO:3", ""],
        ["UPHENO:3", "", E + "2", ""],
        [E + "2", "", "UPHENO:1", ""],
    ])
    assert h.nearest(E + "1", lambda c: c.startswith(E)) == {E + "2"}


def test_exact(tmp_path):
    h = h_from(tmp_path, [[E + "1", "", "UPHENO:1", "UPHENO:7|ZP:3"]])
    assert h.exact(E + "1", is_upheno) == {"UPHENO:7"}


def test_multiple_irredundant_groupings_kept(tmp_path):
    h = h_from(tmp_path, [
        [E + "1", "", "UPHENO:2|UPHENO:3", ""],
        ["UPHENO:2", "", "UPHENO:1", ""],
        ["UPHENO:3", "", "UPHENO:1", ""],
    ])
    assert h.nearest(E + "1", is_upheno) == {"UPHENO:2", "UPHENO:3"}
