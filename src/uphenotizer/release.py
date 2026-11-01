"""Turn the reasoned hierarchy into ROBOT templates (component base + bridge), SSSOM and a summary."""

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from uphenotizer.classify import Hierarchy, is_upheno
from uphenotizer.components import COMPONENTS, Component
from uphenotizer.idmap import ComponentIdMap
from uphenotizer.model import PENDING, ROUTED

UPHENO_IRI = "http://purl.obolibrary.org/obo/UPHENO_"
SUMMARY_MARKER = "## Components and uPheno bridges"
USAGE_NOTE = ("This class is not intended for use in curation or annotation. "
              "Use uPheno classes instead.")


def template_prefix(component: Component) -> str:
    """Prefix used only inside ROBOT templates (ROBOT is picky about dots/hyphens)."""
    return component.name.replace("-", "")


def template_curie(component: Component, iri: str) -> str:
    return f"{template_prefix(component)}:{iri[len(component.iri_base):]}"


@dataclass
class ClassResult:
    iri: str
    key: str
    exact: set[str] = field(default_factory=set)
    groupings: set[str] = field(default_factory=set)
    parents: set[str] = field(default_factory=set)  # in-component
    affects: set[str] = field(default_factory=set)  # bearers: UPHENO:0000001 / UPHENO:0000003

    @property
    def bridge(self) -> set[str]:
        return self.exact or self.groupings


def classify_component(m: ComponentIdMap, h: Hierarchy) -> list[ClassResult]:
    """Every class ever minted is released (no deprecation), so every class is classified."""
    members = {iri for _, iri in m.items()}
    return [ClassResult(iri, key, exact=h.exact(iri, is_upheno),
                        groupings=h.nearest(iri, is_upheno),
                        parents=h.nearest(iri, lambda c: c in members),
                        affects=h.bearers(iri))
            for key, iri in m.items()]


def load_provenance(source_map: str | Path) -> dict[tuple[str, str], tuple[int, str]]:
    """(source, key) -> (annotation count, most frequent example statement)."""
    counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    with open(source_map, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["status"] in (ROUTED, PENDING) and r["key"]:
                counts[(r["source"], r["key"])][r["example_statement"]] += int(r["annotations"])
    return {k: (sum(c.values()), c.most_common(1)[0][0]) for k, c in counts.items()}


def _write(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter="\t", lineterminator="\n").writerows(rows)


def write_templates(component: Component, results: list[ClassResult],
                    provenance: dict, outdir: Path) -> None:
    # Direct phenotype -> entity links, in the exact form PHENIO's extract-upheno-relations adds
    # them (it can't derive them here, because the released classes carry no logical definitions).
    base = [["ID", "parents", "phenotype affects entity", "phenotype is associated with entity",
             "provenance", "usage", "taxon", "subset"],
            ["ID", "SC % SPLIT=|", "SC 'phenotype affects entity' some % SPLIT=|",
             "SC 'phenotype is associated with entity' some % SPLIT=|", "A rdfs:comment",
             "A rdfs:comment", "SC 'in taxon' some %", "AI oboInOwl:inSubset"]]
    bridge = [["ID", "uPheno grouping"], ["ID", "SC % SPLIT=|"]]
    for r in results:
        n, example = provenance.get((component.source, r.key), (0, ""))
        if n:
            noun = "annotation" if n == 1 else "annotations"
            comment = (f"Pre-composed by uphenotizer from {n} {component.source} phenotype {noun}"
                       f" (e.g. \"{example}\"). Key: {r.key}")
        else:
            comment = (f"Pre-composed by uphenotizer; not used by current {component.source} "
                       f"phenotype annotations. Key: {r.key}")
        affects = "|".join(sorted(r.affects))
        base.append([template_curie(component, r.iri),
                     "|".join(sorted(template_curie(component, p) for p in r.parents)),
                     affects, affects, comment, USAGE_NOTE, component.taxon,
                     f"uphenotizer:{component.subset}"])
        if r.bridge:
            bridge.append([template_curie(component, r.iri), "|".join(sorted(r.bridge))])
    _write(outdir / f"{component.name}-base.tsv", base)
    _write(outdir / f"{component.name}-bridge.tsv", bridge)


def write_sssom(component: Component, results: list[ClassResult], h: Hierarchy,
                path: Path) -> None:
    header = [
        "# curie_map:",
        f"#   {component.prefix}: {component.iri_base}",
        f"#   UPHENO: {UPHENO_IRI}",
        "#   semapv: https://w3id.org/semapv/vocab/",
        "#   skos: http://www.w3.org/2004/02/skos/core#",
        f"# mapping_set_id: {component.file_iri('upheno.sssom.tsv')}",
        "# license: https://creativecommons.org/publicdomain/zero/1.0/",
        f"# comment: {component.title}, classified under uPheno by reasoning (uphenotizer).",
    ]
    rows = [["subject_id", "subject_label", "predicate_id", "object_id", "object_label",
             "mapping_justification"]]
    for r in results:
        predicate = "semapv:crossSpeciesExactMatch" if r.exact else "skos:broadMatch"
        for target in sorted(r.bridge):
            rows.append([component.curie(r.iri), h.labels.get(r.iri, ""), predicate, target,
                         h.labels.get(target, ""), "semapv:LogicalReasoning"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n")
        csv.writer(f, delimiter="\t", lineterminator="\n").writerows(rows)


def summary_section(per_component: dict[str, list[ClassResult]], h: Hierarchy, top: int = 10) -> str:
    lines = [SUMMARY_MARKER, "",
             ("| component | classes | equivalent to UPHENO | grouped under UPHENO | "
              "no UPHENO grouping | with in-component parent |"),
             "|---|---:|---:|---:|---:|---:|"]
    tops = {}
    for name, results in per_component.items():
        lines.append(f"| {name} | {len(results)} | {sum(1 for r in results if r.exact)} | "
                     f"{sum(1 for r in results if not r.exact and r.groupings)} | "
                     f"{sum(1 for r in results if not r.bridge)} | "
                     f"{sum(1 for r in results if r.parents)} |")
        tops[name] = Counter(g for r in results for g in r.bridge).most_common(top)
    for name, common in tops.items():
        lines += ["", f"Most frequent uPheno groupings, {name}:", ""]
        lines += [f"- {n} × `{g}` {h.labels.get(g, '')}" for g, n in common]

    lines += ["", "### Duplicate labels within a component", ""]
    duplicates = {name: duplicate_labels(results, h) for name, results in per_component.items()}
    if not any(duplicates.values()):
        lines.append("None.")
    for name, dups in duplicates.items():
        for label, iris in dups.items():
            lines.append(f"- {name}: \"{label}\" on {', '.join(sorted(iris))}. Usually an FBbt term "
                         "duplicating a GO term without an axiom; see `fbbt_as_go` in config/flybase.yaml")
    return "\n".join(lines) + "\n"


def duplicate_labels(results: list[ClassResult], h: Hierarchy) -> dict[str, list[str]]:
    by_label = defaultdict(list)
    for r in results:
        if label := h.labels.get(r.iri):
            by_label[label].append(r.iri)
    return {label: iris for label, iris in sorted(by_label.items()) if len(iris) > 1}


def release(idmap_dir: str | Path, classified: str | Path, source_map: str | Path,
            template_dir: str | Path, mapping_dir: str | Path, summary: str | Path) -> str:
    h = Hierarchy.from_export(classified)
    provenance = load_provenance(source_map)
    per_component = {}
    for component in COMPONENTS.values():
        m = ComponentIdMap(component, Path(idmap_dir) / f"{component.name}.tsv")
        results = classify_component(m, h)
        write_templates(component, results, provenance, Path(template_dir))
        write_sssom(component, results, h, Path(mapping_dir) / f"{component.name}-upheno.sssom.tsv")
        per_component[component.name] = results
    section = summary_section(per_component, h)
    summary = Path(summary)
    text = summary.read_text(encoding="utf-8") if summary.exists() else ""
    text = text.split(SUMMARY_MARKER)[0].rstrip("\n") + "\n\n" + section
    summary.write_text(text, encoding="utf-8")
    return section
