"""Mint component IDs and write the per-component DOSDP tables that dosdp-tools turns into OWL."""

import csv
from collections import defaultdict
from pathlib import Path

from uphenotizer.components import COMPONENTS
from uphenotizer.curie import expand
from uphenotizer.idmap import ComponentIdMap
from uphenotizer.model import PENDING, ROUTED, Outcome
from uphenotizer.upheno import PatternCatalog


def split_key(key: str) -> tuple[list[str], str]:
    """``CURIE-...-CURIE-pattern`` -> (filler CURIEs ordered by var name, pattern)."""
    *fillers, pattern = key.split("-")
    return fillers, pattern


def update_idmaps(outcomes: list[Outcome], idmap_dir: str | Path,
                  sources: set[str]) -> dict[str, ComponentIdMap]:
    """Mint IDs for new keys. Only components whose source was processed are updated (and saved)."""
    keys = defaultdict(set)
    for o in outcomes:
        if o.status in (ROUTED, PENDING):
            keys[o.unit.source].add(o.extra["key"])
    maps = {}
    for source, component in COMPONENTS.items():
        m = ComponentIdMap(component, Path(idmap_dir) / f"{component.name}.tsv")
        if source in sources:
            m.update(keys.get(source, set()))
            m.save()
        maps[source] = m
    return maps


def bind(outcomes: list[Outcome], maps: dict[str, ComponentIdMap]) -> None:
    """Attach the component class ID (``PHENOTYPE:...``) to every routed/pending outcome."""
    for o in outcomes:
        if o.status in (ROUTED, PENDING):
            o.extra["class_id"] = maps[o.unit.source].rows[o.extra["key"]]["id"]


def write_dosdp_tables(maps: dict[str, ComponentIdMap], catalog: PatternCatalog,
                       outdir: str | Path) -> None:
    """tmp/dosdp/<component>/<pattern>.tsv (every key ever minted), the pattern YAMLs and
    fillers.txt (every filler CURIE, for extracting labels)."""
    outdir = Path(outdir)
    fillers_seen: set[str] = set()
    patterns_used: set[str] = set()
    for m in maps.values():
        tables: dict[str, list[list[str]]] = defaultdict(list)
        for key, iri in m.items():
            fillers, pattern = split_key(key)
            tables[pattern].append([iri] + [expand(f) for f in fillers])
            fillers_seen.update(fillers)
            patterns_used.add(pattern)
        d = outdir / m.component.name
        d.mkdir(parents=True, exist_ok=True)
        for stale in d.glob("*.tsv"):
            stale.unlink()
        for pattern, rows in tables.items():
            with open(d / f"{pattern}.tsv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter="\t", lineterminator="\n")
                w.writerow(["defined_class"] + catalog.vars(pattern))
                w.writerows(rows)
    (outdir / "patterns").mkdir(parents=True, exist_ok=True)
    for pattern in sorted(patterns_used):
        (outdir / "patterns" / f"{pattern}.yaml").write_text(catalog.yaml_text(pattern))
    (outdir / "fillers.txt").write_text("".join(f"{c}\n" for c in sorted(fillers_seen)))
