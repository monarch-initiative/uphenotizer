import csv

from uphenotizer.components import COMPONENTS
from uphenotizer.idmap import ComponentIdMap
from uphenotizer.release import SUMMARY_MARKER, release

BASE = "https://w3id.org/monarch-initiative/entity/PHENOTYPE_"


def read(path):
    with open(path) as f:
        return list(csv.reader((line for line in f if not line.startswith("#")), delimiter="\t"))


def setup(tmp_path):
    idmaps = tmp_path / "idmaps"
    m = ComponentIdMap(COMPONENTS["FB"], idmaps / "dpo-ext.tsv")
    m.update({"FBbt:1-abnormalAnatomicalEntity", "FBbt:2-abnormalAnatomicalEntity",
              "GO:1-abnormalBiologicalProcess", "FBbt:9-abnormalAnatomicalEntity"})
    m.update({"FBbt:1-abnormalAnatomicalEntity", "FBbt:2-abnormalAnatomicalEntity",
              "GO:1-abnormalBiologicalProcess"})  # FBbt:9 deprecated
    m.save()
    ids = {k: iri for k, iri, _ in m.items()}
    a, b, g, x = (ids["FBbt:1-abnormalAnatomicalEntity"], ids["FBbt:2-abnormalAnatomicalEntity"],
                  ids["GO:1-abnormalBiologicalProcess"], ids["FBbt:9-abnormalAnatomicalEntity"])
    classified = tmp_path / "classified.tsv"
    classified.write_text(
        "ID\tLABEL\tSubClass Of\tEquivalent Class\n"
        f"{a}\tabnormal A\t{b}\t\n"                       # A below B (in-component)
        f"{b}\tabnormal B\tUPHENO:2\t\n"
        f"{g}\tabnormal G\tUPHENO:1\tUPHENO:7\n"          # exact match
        f"{x}\tabnormal X\tUPHENO:2\t\n"
        "UPHENO:2\tB phenotype\tUPHENO:1\t\n"
        "UPHENO:7\tG phenotype\tUPHENO:1\t\n"
    )
    source_map = tmp_path / "source_map.tsv"
    source_map.write_text(
        "source\tsource_terms\tchemical\tannotations\texample_statement\tstatus\trule\tpattern\tkey"
        "\tdefined_class\treason\n"
        "FB\tFBbt:1\t\t5\tA | recessive\trouted\tr\tabnormalAnatomicalEntity"
        "\tFBbt:1-abnormalAnatomicalEntity\t\t\n"
    )
    summary = tmp_path / "summary.md"
    summary.write_text(f"# run\n\n{SUMMARY_MARKER}\n\nstale\n")
    release(idmaps, classified, source_map, tmp_path / "templates", tmp_path / "mappings", summary)
    return tmp_path, (a, b, g, x)


def tc(iri):
    return "dpoext:" + iri[len(BASE):]


def curie(iri):
    return "PHENOTYPE:" + iri[len(BASE):]


def test_base_template(tmp_path):
    out, (a, b, _g, x) = setup(tmp_path)
    rows = {r[0]: r for r in read(out / "templates" / "dpo-ext-base.tsv")[2:]}
    assert rows[tc(a)][2] == tc(b)                      # in-component parent
    assert rows[tc(b)][2] == ""                         # parent is UPHENO -> bridge, not base
    assert rows[tc(x)][1] == "true"                     # deprecated
    assert "5 FB phenotype annotations" in rows[tc(a)][3]


def test_bridge_template_exact_wins_and_deprecated_excluded(tmp_path):
    out, (a, b, g, x) = setup(tmp_path)
    rows = {r[0]: r[1] for r in read(out / "templates" / "dpo-ext-bridge.tsv")[2:]}
    assert rows[tc(g)] == "UPHENO:7"
    assert rows[tc(b)] == "UPHENO:2"
    assert rows[tc(a)] == "UPHENO:2"                    # through B
    assert tc(x) not in rows


def test_sssom(tmp_path):
    out, (_a, b, g, _x) = setup(tmp_path)
    rows = read(out / "mappings" / "dpo-ext-upheno.sssom.tsv")
    assert rows[0][:3] == ["subject_id", "subject_label", "predicate_id"]
    by_subject = {r[0]: r for r in rows[1:]}
    assert by_subject[curie(g)][2:5] == ["semapv:crossSpeciesExactMatch", "UPHENO:7", "G phenotype"]
    assert by_subject[curie(b)][2] == "skos:broadMatch"
    header = (out / "mappings" / "dpo-ext-upheno.sssom.tsv").read_text()
    assert f"#   PHENOTYPE: {BASE}" in header
    assert "uphenotizer/release/dpo-ext-upheno.sssom.tsv" in header


def test_summary_section_replaced(tmp_path):
    out, _ = setup(tmp_path)
    text = (out / "summary.md").read_text()
    assert "stale" not in text
    assert text.count(SUMMARY_MARKER) == 1
    assert "| dpo-ext | 3 | 1 | 1 | 2 | 0 | 1 |" in text
