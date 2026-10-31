"""Turn the reasoned hierarchy into ROBOT templates (component base + bridge), SSSOM and a summary."""

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from uphenotizer.classify import Hierarchy, is_upheno
from uphenotizer.components import COMPONENTS, Component
from uphenotizer.idmap import ACTIVE, ComponentIdMap
from uphenotizer.model import PENDING, ROUTED

UPHENO_IRI = "http://purl.obolibrary.org/obo/UPHENO_"
SUMMARY_MARKER = "## Components and uPheno bridges"


def template_prefix(component: Component) -> str:
    """Prefix used only inside ROBOT templates (ROBOT is picky about dots/hyphens)."""
    return component.name.replace("-", "")


def template_curie(component: Component, iri: str) -> str:
    return f"{template_prefix(component)}:{iri[len(component.iri_base):]}"


@dataclass
class ClassResult:
    iri: str
    key: str
    active: bool
    exact: set[str] = field(default_factory=set)
    groupings: set[str] = field(default_factory=set)
    parents: set[str] = field(default_factory=set)  # in-component

    @property
    def bridge(self) -> set[str]:
        return self.exact or self.groupings


def classify_component(m: ComponentIdMap, h: Hierarchy) -> list[ClassResult]:
    active = {iri for _, iri, status in m.items() if status == ACTIVE}
    results = []
    for key, iri, status in m.items():
        r = ClassResult(iri, key, status == ACTIVE)
        if r.active:
            r.exact = h.exact(iri, is_upheno)
            r.groupings = h.nearest(iri, is_upheno)
            r.parents = h.nearest(iri, lambda c: c in active)
        results.append(r)
    return results


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
    base = [["ID", "deprecated", "parents", "comment"],
            ["ID", "AT owl:deprecated^^xsd:boolean", "SC % SPLIT=|", "A rdfs:comment"]]
    bridge = [["ID", "uPheno grouping"], ["ID", "SC % SPLIT=|"]]
    for r in results:
        n, example = provenance.get((component.source, r.key), (0, ""))
        noun = "annotation" if n == 1 else "annotations"
        comment = (f"Pre-composed by uphenotizer from {n} {component.source} phenotype {noun}"
                   f" (e.g. \"{example}\"). Key: {r.key}" if r.active else f"Key: {r.key}")
        base.append([template_curie(component, r.iri), "" if r.active else "true",
                     "|".join(sorted(template_curie(component, p) for p in r.parents)), comment])
        if r.active and r.bridge:
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
        if not r.active:
            continue
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
             ("| component | active | deprecated | equivalent to UPHENO | grouped under UPHENO | "
              "no UPHENO grouping | with in-component parent |"),
             "|---|---:|---:|---:|---:|---:|---:|"]
    tops = {}
    for name, results in per_component.items():
        act = [r for r in results if r.active]
        lines.append(f"| {name} | {len(act)} | {len(results) - len(act)} | "
                     f"{sum(1 for r in act if r.exact)} | "
                     f"{sum(1 for r in act if not r.exact and r.groupings)} | "
                     f"{sum(1 for r in act if not r.bridge)} | {sum(1 for r in act if r.parents)} |")
        tops[name] = Counter(g for r in act for g in r.bridge).most_common(top)
    for name, common in tops.items():
        lines += ["", f"Most frequent uPheno groupings, {name}:", ""]
        lines += [f"- {n} × `{g}` {h.labels.get(g, '')}" for g, n in common]
    return "\n".join(lines) + "\n"


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
