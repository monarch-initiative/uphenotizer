"""Shared fixtures: a fake uPheno checkout with a handful of patterns and an ID map."""

import pytest

from uphenotizer.upheno import PatternCatalog, UphenoSource

UP = "http://purl.obolibrary.org/obo/"

PATTERNS = {
    "dosdp-dev/abnormalAnatomicalEntity": ["anatomical_entity"],
    "dosdp-patterns/abnormallyIncreasedNumberOfAnatomicalEntity": ["anatomical_entity"],
    "dosdp-patterns/abnormallyDecreasedNumberOfAnatomicalEntity": ["anatomical_entity"],
    "dosdp-patterns/abnormalBiologicalProcess": ["biological_process"],
    "dosdp-patterns/abnormalCellularComponent": ["cellular_component"],
    "dosdp-patterns/abnormalMolecularFunction": ["molecular_function"],
    "dosdp-patterns/abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity":
        ["chemical_entity"],
    "dosdp-patterns/abnormallyIncreasedResistanceOfWholeOrganismToChemicalEntity":
        ["chemical_entity"],
    "dosdp-patterns/abnormallyDecreasedRateOfBiologicalProcess": ["biological_process"],
}

ID_MAP = (
    "defined_class\tid\n"
    f"{UP}UPHENO_0000002\t{UP}CHEBI_1-abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity.tsv\n"
    f"{UP}UPHENO_0000001\t{UP}CHEBI_1-abnormallyDecreasedResistanceOfWholeOrganismToChemicalEntity.tsv\n"
    f"{UP}UPHENO_0000010\t{UP}GO_0000010-abnormalBiologicalProcess.tsv\n"
)


@pytest.fixture
def upheno_dir(tmp_path):
    root = tmp_path / "upheno"
    for rel, vars_ in PATTERNS.items():
        p = root / "src/patterns" / f"{rel}.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f"  {v}: \"'{v}'\"\n" for v in vars_)
        p.write_text(f"pattern_name: {rel.split('/')[1]}\nvars:\n{body}")
    idmap = root / "src/curation/upheno_id_map.txt"
    idmap.parent.mkdir(parents=True)
    idmap.write_text(ID_MAP)
    return root


@pytest.fixture
def catalog(upheno_dir, tmp_path):
    local = tmp_path / "local_patterns"
    local.mkdir()
    (local / "localOnlyPattern.yaml").write_text("pattern_name: localOnlyPattern\nvars:\n  x: \"'x'\"\n")
    return PatternCatalog(UphenoSource(upheno_dir), local)
