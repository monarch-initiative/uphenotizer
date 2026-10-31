"""Read Alliance PHENOTYPE_<MOD>.json(.gz) dumps and aggregate records into source units."""

import gzip
import json
from collections.abc import Iterable
from pathlib import Path

from uphenotizer.model import Unit


def load_records(path: str | Path) -> list[dict]:
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)["data"]


def ordered_terms(record: dict) -> tuple[str, ...]:
    ids = record.get("phenotypeTermIdentifiers") or []
    ids = sorted(ids, key=lambda t: t.get("termOrder", 0))
    return tuple(t["termId"] for t in ids if t.get("termId"))


CHEMICAL_CONDITION = "ZECO:0000111"
UNMAPPED_CHEMICAL = "unmapped:"


def chemicals(record: dict) -> list[str]:
    """ChEBI IDs of chemical conditions. A chemical condition without a ChEBI ID is kept as
    ``unmapped:<statement>`` so routers can refuse it instead of falling back silently."""
    found = []
    for relation in record.get("conditionRelations") or []:
        for condition in relation.get("conditions") or []:
            chem = condition.get("chemicalOntologyId")
            if not chem and condition.get("conditionClassId") == CHEMICAL_CONDITION:
                chem = UNMAPPED_CHEMICAL + condition.get("conditionStatement", "")
            if chem and chem not in found:
                found.append(chem)
    return found


def _aggregate(source: str, keyed: Iterable[tuple[tuple, dict]]) -> list[Unit]:
    units: dict[tuple, Unit] = {}
    for (terms, chemical), record in keyed:
        unit = units.get((terms, chemical))
        if unit is None:
            unit = Unit(source, terms, chemical, 0, record.get("phenotypeStatement", ""))
            units[(terms, chemical)] = unit
        unit.annotations += 1
    return list(units.values())


def units_flybase(records: list[dict]) -> list[Unit]:
    return _aggregate("FB", (((ordered_terms(r), None), r) for r in records))


def units_sgd(records: list[dict]) -> list[Unit]:
    """One unit per (terms, chemical). A record with several chemicals counts once per chemical."""

    def keyed():
        for r in records:
            terms = ordered_terms(r)
            for chem in chemicals(r) or [None]:
                yield (terms, chem), r

    return _aggregate("SGD", keyed())
